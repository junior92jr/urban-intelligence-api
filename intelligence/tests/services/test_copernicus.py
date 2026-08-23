from datetime import UTC, date, datetime
from pathlib import Path
from typing import cast
from unittest.mock import Mock

import numpy as np
import pytest
import rasterio  # type: ignore[import-untyped]
from chainmock import mocker
from django.conf import settings
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.test import override_settings
from rasterio.transform import from_origin  # type: ignore[import-untyped]

from geo.models import ServiceArea
from intelligence.models import (
    AreaIndicatorObservation,
    IntelligenceDataset,
    IntelligenceImport,
)
from intelligence.services.imports import (
    IntelligenceImportConfigurationError,
    run_intelligence_import,
)
from intelligence.services.providers import copernicus

pytestmark = pytest.mark.django_db


def create_tree_cover_raster(path: Path) -> None:
    values = np.array([[10, 20], [30, 255]], dtype=np.uint8)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype=values.dtype,
        crs="EPSG:3035",
        transform=from_origin(4_320_000, 3_200_200, 100, 100),
        nodata=255,
    ) as raster:
        raster.write(values, 1)


def set_service_area_boundary(service_area: ServiceArea) -> None:
    boundary = MultiPolygon(
        Polygon(
            (
                (4_319_990, 3_199_990),
                (4_320_210, 3_199_990),
                (4_320_210, 3_200_210),
                (4_319_990, 3_200_210),
                (4_319_990, 3_199_990),
            ),
            srid=3035,
        ),
        srid=3035,
    )
    service_area.boundary = cast(
        MultiPolygon,
        boundary.transform(4326, clone=True),
    )
    service_area.save(update_fields=["boundary"])


def build_catalog_entry(
    *,
    name: str,
    reference_date: str,
    bbox: str,
) -> copernicus.TreeCoverDensityCatalogEntry:
    return copernicus.TreeCoverDensityCatalogEntry(
        name=name,
        content_date_start=datetime.fromisoformat(f"{reference_date}T00:00:00+00:00"),
        checksum_value=f"checksum-{name}",
        s3_path=(f"s3://eodata/CLMS/landcover_landuse/tree_cover_density/{name}"),
        bbox=bbox,
    )


def test_tree_cover_density_import_creates_green_exposure_observation(
    tmp_path: Path,
) -> None:
    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")
    set_service_area_boundary(service_area)
    dataset = IntelligenceDataset.objects.get(slug="tree-cover-density-100m")
    intelligence_import = IntelligenceImport.objects.create(
        dataset=dataset,
        service_area=service_area,
    )
    raster_path = tmp_path / "tree-cover-density.tif"
    create_tree_cover_raster(raster_path)
    tile = build_catalog_entry(
        name="frankfurt-2024",
        reference_date="2024-01-01",
        bbox="POLYGON((8.6 50.0,8.6 50.2,8.8 50.2,8.8 50.0,8.6 50.0))",
    )
    mocker(copernicus).mock("validate_configuration").called_once()
    mocker(copernicus).mock(
        "select_tree_cover_density_tiles"
    ).called_once().return_value(([tile], date(2024, 1, 1)))
    mocker(copernicus).mock(
        "download_tree_cover_density_tile"
    ).called_once().return_value(
        copernicus.DownloadedRaster(
            path=raster_path,
            sha256="test-checksum",
            cache_object_key="copernicus/tree-cover-density/2024/checksum/frankfurt.tif",
        )
    )
    mocker(copernicus).mock("upload_tree_cover_density_overlay").called_once()

    result_count = run_intelligence_import(intelligence_import)

    intelligence_import.refresh_from_db()
    observation = AreaIndicatorObservation.objects.get(
        service_area=service_area,
        indicator=dataset.indicator,
        source=dataset.source,
        observed_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    assert result_count == 1
    assert intelligence_import.status == IntelligenceImport.Status.COMPLETED
    assert intelligence_import.dataset_version == "v1"
    assert intelligence_import.reference_date == date(2024, 1, 1)
    assert intelligence_import.metadata["catalog_url"] == (
        settings.COPERNICUS_TREE_COVER_DENSITY_CATALOG_URL
    )
    assert intelligence_import.metadata["tile_count"] == 1
    assert intelligence_import.metadata["cached_object_keys"] == [
        "copernicus/tree-cover-density/2024/checksum/frankfurt.tif"
    ]
    assert intelligence_import.metadata["overlay_object_keys"] == [
        (
            "copernicus/tree-cover-density/overlays/2024-01-01/"
            "checksum-frankfurt-2024/frankfurt-am-main/frankfurt-2024.png"
        )
    ]
    assert observation.score == 20
    assert observation.details["raw_value_percent"] == 20.0
    assert observation.details["tile_count"] == 1
    assert observation.details["map_layer"]["title"] == "Tree cover"
    assert observation.details["map_layer"]["layers"][0]["object_key"] == (
        "copernicus/tree-cover-density/overlays/2024-01-01/"
        "checksum-frankfurt-2024/frankfurt-am-main/frankfurt-2024.png"
    )
    assert len(observation.details["map_layer"]["layers"][0]["bounds"]) == 2
    assert not raster_path.exists()


def test_encode_tree_cover_png_creates_a_transparent_png() -> None:
    values = np.ma.masked_array(
        [[0, 100]],
        mask=[[False, True]],
    )

    image = copernicus.encode_tree_cover_png(values)

    assert image.startswith(b"\x89PNG\r\n\x1a\n")


def test_tree_cover_density_import_requires_a_service_area_boundary() -> None:
    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")
    service_area.boundary = None
    service_area.save(update_fields=["boundary"])
    dataset = IntelligenceDataset.objects.get(slug="tree-cover-density-100m")
    intelligence_import = IntelligenceImport.objects.create(
        dataset=dataset,
        service_area=service_area,
    )

    with pytest.raises(IntelligenceImportConfigurationError, match="needs a boundary"):
        copernicus.import_tree_cover_density(intelligence_import)


def test_select_tree_cover_density_tiles_uses_latest_overlapping_date() -> None:
    boundary = MultiPolygon(
        Polygon(
            (
                (8.6, 50.0),
                (8.6, 50.2),
                (8.8, 50.2),
                (8.8, 50.0),
                (8.6, 50.0),
            ),
            srid=4326,
        ),
        srid=4326,
    )
    old_tile = build_catalog_entry(
        name="frankfurt-2023",
        reference_date="2023-01-01",
        bbox="POLYGON((8.5 49.9,8.5 50.3,8.9 50.3,8.9 49.9,8.5 49.9))",
    )
    latest_tile = build_catalog_entry(
        name="frankfurt-2024",
        reference_date="2024-01-01",
        bbox="POLYGON((8.5 49.9,8.5 50.3,8.9 50.3,8.9 49.9,8.5 49.9))",
    )
    non_overlapping_tile = build_catalog_entry(
        name="berlin-2024",
        reference_date="2024-01-01",
        bbox="POLYGON((13.2 52.4,13.2 52.6,13.6 52.6,13.6 52.4,13.2 52.4))",
    )
    mocker(copernicus).mock("fetch_tree_cover_density_catalog").return_value(
        [old_tile, latest_tile, non_overlapping_tile]
    )

    selected_tiles, reference_date = copernicus.select_tree_cover_density_tiles(
        boundary=boundary
    )

    assert selected_tiles == [latest_tile]
    assert reference_date == date(2024, 1, 1)


def test_find_source_raster_key_selects_only_the_geotiff_asset() -> None:
    tile = build_catalog_entry(
        name="frankfurt-2024",
        reference_date="2024-01-01",
        bbox="POLYGON((8.6 50.0,8.6 50.2,8.8 50.2,8.8 50.0,8.6 50.0))",
    )
    source_client = Mock()
    source_client.list_objects_v2.return_value = {
        "Contents": [
            {"Key": f"{tile.source_prefix}/{tile.name}.xml"},
            {"Key": f"{tile.source_prefix}/{tile.name}.tif.aux.xml"},
            {"Key": f"{tile.source_prefix}/{tile.name}.tif"},
        ]
    }
    mocker(copernicus).mock("get_copernicus_source_client").return_value(source_client)

    source_key = copernicus.find_source_raster_key(tile)

    assert source_key == f"{tile.source_prefix}/{tile.name}.tif"
    source_client.list_objects_v2.assert_called_once_with(
        Bucket="eodata",
        Prefix=tile.source_prefix,
    )


def test_tree_cover_density_configuration_requires_a_cache_bucket() -> None:
    with (
        override_settings(OBJECT_STORAGE_BUCKET=""),
        pytest.raises(
            IntelligenceImportConfigurationError,
            match="OBJECT_STORAGE_BUCKET",
        ),
    ):
        copernicus.validate_configuration()
