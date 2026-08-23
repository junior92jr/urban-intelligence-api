import csv
import hashlib
import json
import struct
import tempfile
import zlib
from datetime import UTC, date, datetime, time
from io import StringIO
from pathlib import Path
from typing import Any

import boto3  # type: ignore[import-untyped]
import httpx
import numpy as np
import rasterio  # type: ignore[import-untyped]
from botocore.config import Config  # type: ignore[import-untyped]
from botocore.exceptions import (  # type: ignore[import-untyped]
    BotoCoreError,
    ClientError,
)
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django.db import transaction
from pydantic import BaseModel, ConfigDict
from rasterio.mask import mask  # type: ignore[import-untyped]
from rasterio.transform import array_bounds  # type: ignore[import-untyped]
from rasterio.warp import transform_bounds  # type: ignore[import-untyped]

from intelligence.models import AreaIndicatorObservation, IntelligenceImport
from intelligence.services.imports import (
    IntelligenceImportConfigurationError,
    IntelligenceImportResult,
    IntelligenceProviderUnavailable,
)

TREE_COVER_DENSITY_VERSION = "v1"
COPERNICUS_SOURCE_BUCKET = "eodata"


class TreeCoverDensityCatalogEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    content_date_start: datetime
    checksum_value: str
    s3_path: str
    bbox: str

    @property
    def reference_date(self) -> date:
        return self.content_date_start.date()

    @property
    def source_prefix(self) -> str:
        return self.s3_path.removeprefix(f"s3://{COPERNICUS_SOURCE_BUCKET}/")

    @property
    def boundary(self) -> GEOSGeometry:
        return GEOSGeometry(self.bbox, srid=4326)

    @property
    def cache_object_key(self) -> str:
        return (
            "copernicus/tree-cover-density/"
            f"{self.reference_date.isoformat()}/{self.checksum_value}/{self.name}.tif"
        )


class DownloadedRaster(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: Path
    sha256: str
    cache_object_key: str


class GeneratedRasterOverlay(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: Path
    object_key: str
    bounds: list[list[float]]


def import_tree_cover_density(
    intelligence_import: IntelligenceImport,
) -> IntelligenceImportResult:
    boundary = intelligence_import.service_area.boundary
    if boundary is None:
        raise IntelligenceImportConfigurationError(
            "The service area needs a boundary before Tree Cover Density can be imported."
        )

    validate_configuration()
    tiles, reference_date = select_tree_cover_density_tiles(boundary=boundary)
    total_value = 0.0
    total_pixel_count = 0
    resolution_meters: float | None = None
    cached_object_keys: list[str] = []
    overlays: list[GeneratedRasterOverlay] = []

    for tile in tiles:
        downloaded_raster = download_tree_cover_density_tile(tile)
        try:
            raw_score, valid_pixel_count, tile_resolution_meters = (
                calculate_tree_cover_density(
                    raster_path=downloaded_raster.path,
                    boundary=boundary,
                )
            )
            overlay = create_tree_cover_density_overlay(
                raster_path=downloaded_raster.path,
                boundary=boundary,
                object_key=build_overlay_object_key(
                    tile=tile,
                    service_area_slug=intelligence_import.service_area.slug,
                ),
            )
            try:
                upload_tree_cover_density_overlay(overlay)
            except Exception:
                overlay.path.unlink(missing_ok=True)
                raise
            overlays.append(overlay)
        finally:
            downloaded_raster.path.unlink(missing_ok=True)

        total_value += raw_score * valid_pixel_count
        total_pixel_count += valid_pixel_count
        resolution_meters = tile_resolution_meters
        cached_object_keys.append(downloaded_raster.cache_object_key)

    if total_pixel_count == 0 or resolution_meters is None:
        raise IntelligenceImportConfigurationError(
            "No valid Tree Cover Density pixels were found for the service area."
        )

    raw_score = total_value / total_pixel_count
    score = max(0, min(100, round(raw_score)))
    observed_at = datetime.combine(reference_date, time.min, tzinfo=UTC)
    details: dict[str, object] = {
        "raw_value_percent": round(raw_score, 2),
        "valid_pixel_count": total_pixel_count,
        "resolution_meters": resolution_meters,
        "tile_count": len(tiles),
        "methodology": "Mean Tree Cover Density within the service-area boundary.",
        "map_layer": {
            "title": "Tree cover",
            "layers": [
                {
                    "object_key": overlay.object_key,
                    "bounds": overlay.bounds,
                }
                for overlay in overlays
            ],
        },
    }

    for overlay in overlays:
        overlay.path.unlink(missing_ok=True)

    with transaction.atomic():
        AreaIndicatorObservation.objects.update_or_create(
            service_area=intelligence_import.service_area,
            indicator=intelligence_import.dataset.indicator,
            source=intelligence_import.dataset.source,
            observed_at=observed_at,
            defaults={
                "score": score,
                "trend": "",
                "methodology": "Mean Tree Cover Density within the service-area boundary.",
                "details": details,
                "expires_at": None,
            },
        )

    return IntelligenceImportResult(
        result_count=1,
        dataset_version=TREE_COVER_DENSITY_VERSION,
        reference_date=reference_date,
        metadata={
            "catalog_url": settings.COPERNICUS_TREE_COVER_DENSITY_CATALOG_URL,
            "tile_count": len(tiles),
            "cached_object_keys": cached_object_keys,
            "overlay_object_keys": [overlay.object_key for overlay in overlays],
            "source_tiles": [
                {
                    "name": tile.name,
                    "checksum": tile.checksum_value,
                    "s3_path": tile.s3_path,
                }
                for tile in tiles
            ],
        },
    )


def build_overlay_object_key(
    *,
    tile: TreeCoverDensityCatalogEntry,
    service_area_slug: str,
) -> str:
    return (
        "copernicus/tree-cover-density/overlays/"
        f"{tile.reference_date.isoformat()}/{tile.checksum_value}/"
        f"{service_area_slug}/{tile.name}.png"
    )


def create_tree_cover_density_overlay(
    *,
    raster_path: Path,
    boundary: Any,
    object_key: str,
) -> GeneratedRasterOverlay:
    with rasterio.open(raster_path) as raster:
        if raster.crs is None:
            raise IntelligenceImportConfigurationError(
                "Tree Cover Density raster has no coordinate reference system."
            )

        boundary_in_raster_crs = boundary.clone()
        boundary_in_raster_crs.transform(raster.crs.to_epsg())
        values, transform = mask(
            raster,
            [json.loads(boundary_in_raster_crs.geojson)],
            indexes=1,
            crop=True,
            filled=False,
        )
        height, width = values.shape
        west, south, east, north = array_bounds(height, width, transform)
        west, south, east, north = transform_bounds(
            raster.crs,
            "EPSG:4326",
            west,
            south,
            east,
            north,
            densify_pts=21,
        )

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temporary_file:
        overlay_path = Path(temporary_file.name)

    overlay_path.write_bytes(encode_tree_cover_png(values))
    return GeneratedRasterOverlay(
        path=overlay_path,
        object_key=object_key,
        bounds=[[south, west], [north, east]],
    )


def upload_tree_cover_density_overlay(overlay: GeneratedRasterOverlay) -> None:
    try:
        get_cache_storage_client().upload_file(
            str(overlay.path),
            settings.OBJECT_STORAGE_BUCKET,
            overlay.object_key,
            ExtraArgs={"ContentType": "image/png"},
        )
    except (BotoCoreError, ClientError) as exc:
        raise IntelligenceProviderUnavailable(
            "Copernicus Tree Cover Density overlay could not be cached."
        ) from exc


def encode_tree_cover_png(values: Any) -> bytes:
    data = values.filled(0)
    mask_data = values.mask
    if not hasattr(mask_data, "shape"):
        mask_data = np.zeros(data.shape, dtype=bool)

    height, width = data.shape
    rows = bytearray()
    for row_index in range(height):
        rows.append(0)
        for column_index in range(width):
            if bool(mask_data[row_index, column_index]):
                rows.extend((0, 0, 0, 0))
                continue

            ratio = max(0.0, min(1.0, float(data[row_index, column_index]) / 100))
            rows.extend(
                (
                    round(226 - (190 * ratio)),
                    round(235 - (110 * ratio)),
                    round(198 - (134 * ratio)),
                    170,
                )
            )

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"".join(
        (
            b"\x89PNG\r\n\x1a\n",
            png_chunk(b"IHDR", header),
            png_chunk(b"IDAT", zlib.compress(bytes(rows))),
            png_chunk(b"IEND", b""),
        )
    )


def png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    return b"".join(
        (
            struct.pack(">I", len(payload)),
            chunk_type,
            payload,
            struct.pack(">I", zlib.crc32(chunk_type + payload)),
        )
    )


def validate_configuration() -> None:
    required_settings = (
        "OBJECT_STORAGE_ENDPOINT_URL",
        "OBJECT_STORAGE_ACCESS_KEY_ID",
        "OBJECT_STORAGE_SECRET_ACCESS_KEY",
        "OBJECT_STORAGE_BUCKET",
        "COPERNICUS_S3_ACCESS_KEY_ID",
        "COPERNICUS_S3_SECRET_ACCESS_KEY",
    )
    missing_settings = [
        setting_name
        for setting_name in required_settings
        if not getattr(settings, setting_name)
    ]
    if missing_settings:
        raise IntelligenceImportConfigurationError(
            f"Missing Tree Cover Density configuration: {', '.join(missing_settings)}."
        )


def select_tree_cover_density_tiles(
    *,
    boundary: GEOSGeometry,
) -> tuple[list[TreeCoverDensityCatalogEntry], date]:
    matching_tiles = [
        entry
        for entry in fetch_tree_cover_density_catalog()
        if boundary.intersection(entry.boundary).area > 0
    ]
    if not matching_tiles:
        raise IntelligenceImportConfigurationError(
            "No Tree Cover Density source tiles overlap the service area."
        )

    reference_date = max(entry.reference_date for entry in matching_tiles)
    return (
        [entry for entry in matching_tiles if entry.reference_date == reference_date],
        reference_date,
    )


def fetch_tree_cover_density_catalog() -> list[TreeCoverDensityCatalogEntry]:
    try:
        response = httpx.get(
            settings.COPERNICUS_TREE_COVER_DENSITY_CATALOG_URL,
            timeout=settings.OBJECT_STORAGE_TIMEOUT_IN_SECS,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise IntelligenceProviderUnavailable(
            "Copernicus Tree Cover Density catalogue could not be downloaded."
        ) from exc

    try:
        return [
            TreeCoverDensityCatalogEntry.model_validate(row)
            for row in csv.DictReader(StringIO(response.text), delimiter=";")
        ]
    except ValueError as exc:
        raise IntelligenceProviderUnavailable(
            "Copernicus Tree Cover Density catalogue could not be parsed."
        ) from exc


def download_tree_cover_density_tile(
    tile: TreeCoverDensityCatalogEntry,
) -> DownloadedRaster:
    cached_raster = download_cached_raster(tile)
    if cached_raster is not None:
        return cached_raster

    source_key = find_source_raster_key(tile)
    downloaded_raster = download_s3_object(
        client=get_copernicus_source_client(),
        bucket=COPERNICUS_SOURCE_BUCKET,
        object_key=source_key,
        cache_object_key=tile.cache_object_key,
    )
    try:
        get_cache_storage_client().upload_file(
            str(downloaded_raster.path),
            settings.OBJECT_STORAGE_BUCKET,
            tile.cache_object_key,
            ExtraArgs={
                "Metadata": {
                    "copernicus-checksum": tile.checksum_value,
                    "copernicus-source-path": tile.s3_path,
                }
            },
        )
    except (BotoCoreError, ClientError) as exc:
        downloaded_raster.path.unlink(missing_ok=True)
        raise IntelligenceProviderUnavailable(
            "Copernicus Tree Cover Density could not be cached in object storage."
        ) from exc

    return downloaded_raster


def download_cached_raster(
    tile: TreeCoverDensityCatalogEntry,
) -> DownloadedRaster | None:
    try:
        return download_s3_object(
            client=get_cache_storage_client(),
            bucket=settings.OBJECT_STORAGE_BUCKET,
            object_key=tile.cache_object_key,
            cache_object_key=tile.cache_object_key,
        )
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code not in {"404", "NoSuchKey", "NoSuchObject"}:
            raise IntelligenceProviderUnavailable(
                "Copernicus Tree Cover Density cache could not be read."
            ) from exc
        return None
    except BotoCoreError as exc:
        raise IntelligenceProviderUnavailable(
            "Copernicus Tree Cover Density cache could not be read."
        ) from exc


def find_source_raster_key(tile: TreeCoverDensityCatalogEntry) -> str:
    try:
        response = get_copernicus_source_client().list_objects_v2(
            Bucket=COPERNICUS_SOURCE_BUCKET,
            Prefix=tile.source_prefix,
        )
    except (BotoCoreError, ClientError) as exc:
        raise IntelligenceProviderUnavailable(
            "Copernicus Tree Cover Density source tile could not be listed."
        ) from exc

    for source_object in response.get("Contents", []):
        object_key = source_object["Key"]
        if object_key.endswith(".tif"):
            return str(object_key)

    raise IntelligenceImportConfigurationError(
        f"Copernicus source tile {tile.name} has no GeoTIFF asset."
    )


def download_s3_object(
    *,
    client: Any,
    bucket: str,
    object_key: str,
    cache_object_key: str,
) -> DownloadedRaster:
    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as temporary_file:
        path = Path(temporary_file.name)

    digest = hashlib.sha256()
    try:
        response = client.get_object(Bucket=bucket, Key=object_key)
        body = response["Body"]
        try:
            with path.open("wb") as raster_file:
                while chunk := body.read(1024 * 1024):
                    digest.update(chunk)
                    raster_file.write(chunk)
        finally:
            body.close()
    except (BotoCoreError, ClientError):
        path.unlink(missing_ok=True)
        raise

    return DownloadedRaster(
        path=path,
        sha256=digest.hexdigest(),
        cache_object_key=cache_object_key,
    )


def get_copernicus_source_client() -> Any:
    return boto3.client(
        "s3",
        endpoint_url=settings.COPERNICUS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.COPERNICUS_S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.COPERNICUS_S3_SECRET_ACCESS_KEY,
        region_name=settings.COPERNICUS_S3_REGION,
        config=get_storage_client_config(),
    )


def get_cache_storage_client() -> Any:
    return boto3.client(
        "s3",
        endpoint_url=settings.OBJECT_STORAGE_ENDPOINT_URL,
        aws_access_key_id=settings.OBJECT_STORAGE_ACCESS_KEY_ID,
        aws_secret_access_key=settings.OBJECT_STORAGE_SECRET_ACCESS_KEY,
        region_name=settings.OBJECT_STORAGE_REGION,
        config=get_storage_client_config(),
    )


def get_storage_client_config() -> Config:
    return Config(
        connect_timeout=settings.OBJECT_STORAGE_TIMEOUT_IN_SECS,
        read_timeout=settings.OBJECT_STORAGE_TIMEOUT_IN_SECS,
    )


def calculate_tree_cover_density(
    *,
    raster_path: Path,
    boundary: Any,
) -> tuple[float, int, float]:
    with rasterio.open(raster_path) as raster:
        raster_srid = raster.crs.to_epsg() if raster.crs is not None else None
        if raster_srid is None:
            raise IntelligenceImportConfigurationError(
                "Tree Cover Density raster has no EPSG coordinate reference system."
            )

        boundary_in_raster_crs = boundary.clone()
        boundary_in_raster_crs.transform(raster_srid)
        shapes = [json.loads(boundary_in_raster_crs.geojson)]
        values, transform = mask(raster, shapes, indexes=1, crop=True, filled=False)
        valid_values = values.compressed()

    if valid_values.size == 0:
        raise IntelligenceImportConfigurationError(
            "The service area does not overlap the Tree Cover Density raster."
        )

    resolution_meters = max(abs(float(transform.a)), abs(float(transform.e)))
    return float(valid_values.mean()), int(valid_values.size), resolution_meters
