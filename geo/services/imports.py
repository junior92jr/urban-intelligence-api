import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.contrib.gis.geos import GEOSException, GEOSGeometry, MultiPolygon, Polygon
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from geo.models import Country, OsmImportRun, ServiceArea
from geo.services.osm.source import (
    archive_latest_extract,
    get_supported_city,
    materialize_archived_extract,
)
from intelligence.services.providers.copernicus import get_cache_storage_client


class OsmImportConfigurationError(Exception):
    """Raised when an OSM administrative-boundaries source is invalid."""


class OsmImportSourceUnavailable(Exception):
    """Raised when the configured object-store source cannot be read."""


@dataclass(frozen=True)
class ImportedArea:
    country_code: str
    name: str
    slug: str
    area_type: str
    boundary: MultiPolygon
    source_id: str
    osm_element_type: str
    osm_admin_level: int | None
    osm_tags: dict[str, object]
    population: int | None
    timezone: str
    parent_identity: tuple[str, str] | None


def run_osm_import(osm_import_run: OsmImportRun) -> int:
    osm_import_run.status = OsmImportRun.Status.RUNNING
    osm_import_run.started_at = timezone.now()
    osm_import_run.finished_at = None
    osm_import_run.error_summary = ""
    osm_import_run.current_stage = "Preparing OSM source"
    osm_import_run.save(
        update_fields=[
            "status",
            "started_at",
            "finished_at",
            "error_summary",
            "current_stage",
        ]
    )

    if osm_import_run.city_slug:
        city = get_supported_city(osm_import_run.city_slug)
        archived_source = archive_latest_extract(city)
        osm_import_run.source_object_key = archived_source.object_key
        osm_import_run.source_sha256 = archived_source.sha256
        osm_import_run.current_stage = "Extracting administrative boundaries from PBF"
        osm_import_run.save(
            update_fields=["source_object_key", "source_sha256", "current_stage"]
        )
        materialized_source = materialize_archived_extract(archived_source)
        try:
            source_bytes = extract_city_hierarchy_geojson(
                city, materialized_source.path
            )
        finally:
            materialized_source.path.unlink(missing_ok=True)
    else:
        source_bytes = download_source(osm_import_run.source_object_key)
    areas = parse_source(source_bytes)
    city_count = sum(area.area_type == ServiceArea.AreaType.CITY for area in areas)
    if city_count == 0:
        raise OsmImportConfigurationError("The source must contain at least one city.")

    osm_import_run.source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    osm_import_run.total_cities = city_count
    osm_import_run.processed_cities = 0
    osm_import_run.current_stage = "Validating and persisting service areas"
    osm_import_run.save(
        update_fields=[
            "source_sha256",
            "total_cities",
            "processed_cities",
            "current_stage",
        ]
    )

    with transaction.atomic():
        active_runs = OsmImportRun.objects.select_for_update().filter(is_active=True)
        if osm_import_run.city_slug:
            active_runs = active_runs.filter(city_slug=osm_import_run.city_slug)
        else:
            active_runs = active_runs.filter(city_slug="")
        active_runs.update(
            is_active=False,
            status=OsmImportRun.Status.SUPERSEDED,
            finished_at=timezone.now(),
        )
        created_areas = create_service_areas(osm_import_run, areas)
        osm_import_run.processed_cities = city_count
        osm_import_run.status = OsmImportRun.Status.SUCCEEDED
        osm_import_run.is_active = True
        osm_import_run.finished_at = timezone.now()
        osm_import_run.current_stage = "Completed"
        osm_import_run.save(
            update_fields=[
                "processed_cities",
                "status",
                "is_active",
                "finished_at",
                "current_stage",
            ]
        )

    return len(created_areas)


def extract_city_geojson(city: object, pbf_path: object) -> bytes:
    """Read the configured city boundary from a PBF as GeoJSON."""
    from geo.services.osm.schemas import SupportedCity

    assert isinstance(city, SupportedCity)
    where = "boundary = 'administrative'"
    if city.osm_relation_id:
        where += f" AND osm_id = {quote_ogr_value(city.osm_relation_id)}"
    else:
        where += f" AND name = {quote_ogr_value(city.name)}"

    features = run_ogr_geojson(pbf_path, where)
    if len(features) != 1:
        raise OsmImportConfigurationError(
            f"Expected one administrative city boundary for {city.name}."
        )

    city_feature = normalize_osm_feature(city, features[0], "city")
    if city.city_admin_level is not None and str(city.city_admin_level) != str(
        feature_properties(city_feature).get("osm_admin_level")
    ):
        raise OsmImportConfigurationError(
            "Configured city admin level did not match OSM."
        )
    return json.dumps(
        {"type": "FeatureCollection", "features": [city_feature]}
    ).encode()


def extract_city_hierarchy_geojson(city: object, pbf_path: object) -> bytes:
    """Return configured city, district and neighborhood boundaries unchanged."""
    from geo.services.osm.schemas import SupportedCity

    assert isinstance(city, SupportedCity)
    city_features = json.loads(extract_city_geojson(city, pbf_path))["features"]
    city_feature = city_features[0]
    city_boundary = parse_boundary(city_feature["geometry"])

    districts = extract_admin_features(
        city,
        pbf_path,
        city.district_admin_levels,
        "district",
        spatial_filter=city_boundary.extent,
    )
    neighborhoods = extract_admin_features(
        city,
        pbf_path,
        city.neighborhood_admin_levels,
        "neighborhood",
        spatial_filter=city_boundary.extent,
    )

    districts = filter_features_inside_boundary(districts, city_boundary)
    neighborhoods = filter_features_inside_boundary(neighborhoods, city_boundary)
    city_identity = feature_identity(city_feature)
    for feature in districts:
        feature_properties(feature).update(
            {
                "parent_source_id": city_identity[1],
                "parent_osm_element_type": city_identity[0],
            }
        )

    district_boundaries = [
        (feature, parse_boundary(feature.get("geometry"))) for feature in districts
    ]
    for feature in neighborhoods:
        neighborhood_point = parse_boundary(feature.get("geometry")).point_on_surface
        matches = [
            district
            for district, boundary in district_boundaries
            if boundary.covers(neighborhood_point)
        ]
        if len(matches) > 1:
            raise OsmImportConfigurationError(
                "Each neighborhood must have at most one district parent."
            )
        parent = (
            feature_properties(matches[0])
            if matches
            else feature_properties(city_feature)
        )
        feature_properties(feature).update(
            {
                "parent_source_id": str(parent["source_id"]),
                "parent_osm_element_type": str(parent["osm_element_type"]),
            }
        )

    document = {
        "type": "FeatureCollection",
        "features": [city_feature, *districts, *neighborhoods],
    }
    return json.dumps(document).encode()


def extract_admin_features(
    city: object,
    pbf_path: object,
    admin_levels: tuple[int, ...],
    area_type: str,
    *,
    spatial_filter: tuple[float, float, float, float] | None = None,
) -> list[dict[str, object]]:
    """Read configured administrative levels from a regional PBF extract."""
    from geo.services.osm.schemas import SupportedCity

    assert isinstance(city, SupportedCity)
    if not admin_levels:
        return []

    level_values = ", ".join(quote_ogr_value(str(level)) for level in admin_levels)
    where = f"boundary = 'administrative' AND admin_level IN ({level_values})"
    return [
        normalize_osm_feature(city, feature, area_type)
        for feature in run_ogr_geojson(pbf_path, where, spatial_filter=spatial_filter)
    ]


def run_ogr_geojson(
    pbf_path: object,
    where: str,
    *,
    spatial_filter: tuple[float, float, float, float] | None = None,
) -> list[dict[str, object]]:
    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as output:
        output_path = Path(output.name)
    output_path.unlink(missing_ok=True)
    try:
        command = [
            "ogr2ogr",
            "-f",
            "GeoJSON",
            str(output_path),
            str(pbf_path),
            "multipolygons",
        ]
        if spatial_filter is not None:
            command.extend(["-spat", *(str(value) for value in spatial_filter)])
        command.extend(
            [
                "-where",
                where,
                "-select",
                "osm_id,osm_way_id,name,admin_level,boundary,other_tags",
            ]
        )
        result = subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=True,
            env={**os.environ, "OGR_INTERLEAVED_READING": "YES"},
        )
        if result.returncode:
            raise OsmImportSourceUnavailable(
                result.stderr or "GDAL could not read PBF."
            )
        with output_path.open(encoding="utf-8") as output_file:
            document = json.load(output_file)
    finally:
        output_path.unlink(missing_ok=True)

    features = document.get("features")
    if not isinstance(features, list):
        raise OsmImportConfigurationError("GDAL did not produce GeoJSON features.")
    return [feature for feature in features if isinstance(feature, dict)]


def normalize_osm_feature(
    city: object,
    feature: dict[str, object],
    area_type: str,
) -> dict[str, object]:
    from geo.services.osm.schemas import SupportedCity

    assert isinstance(city, SupportedCity)
    properties = feature_properties(feature)
    if properties.get("boundary") != "administrative":
        raise OsmImportConfigurationError(
            "Only administrative OSM boundaries can be imported."
        )

    parse_boundary(feature.get("geometry"))
    source_id, element_type = osm_identity(properties)
    osm_tags = parse_other_tags(properties.get("other_tags"))
    properties["name"] = osm_feature_name(properties, osm_tags)
    properties.update(
        {
            "country_code": city.country_code,
            "area_type": area_type,
            "source_id": source_id,
            "osm_element_type": element_type,
            "osm_admin_level": properties.get("admin_level"),
            "osm_tags": osm_tags,
        }
    )
    properties.pop("parent_source_id", None)
    properties.pop("parent_osm_element_type", None)
    return feature


def osm_feature_name(properties: dict[str, object], osm_tags: dict[str, object]) -> str:
    """Return a usable display name for OSM administrative boundaries."""
    for value in (properties.get("name"), osm_tags.get("official_name")):
        if isinstance(value, str) and value.strip():
            return value.strip()

    prefix = osm_tags.get("name:prefix")
    reference = osm_tags.get("ref")
    if (
        isinstance(prefix, str)
        and prefix.strip()
        and isinstance(reference, str)
        and reference.strip()
    ):
        return f"{prefix.strip()} {reference.strip()}"
    raise OsmImportConfigurationError("Every OSM feature needs a name or reference.")


def feature_properties(feature: dict[str, object]) -> dict[str, object]:
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        raise OsmImportConfigurationError("Every OSM feature needs properties.")
    return properties


def osm_identity(properties: dict[str, object]) -> tuple[str, str]:
    osm_id = properties.get("osm_id")
    if osm_id not in (None, ""):
        return (str(osm_id), ServiceArea.OsmElementType.RELATION)

    osm_way_id = properties.get("osm_way_id")
    if osm_way_id not in (None, ""):
        return (str(osm_way_id), ServiceArea.OsmElementType.WAY)

    raise OsmImportConfigurationError("Every OSM feature needs osm_id or osm_way_id.")


def feature_identity(feature: dict[str, object]) -> tuple[str, str]:
    properties = feature_properties(feature)
    return (
        required_string(properties, "osm_element_type"),
        required_string(properties, "source_id"),
    )


def filter_features_inside_boundary(
    features: list[dict[str, object]],
    boundary: MultiPolygon,
) -> list[dict[str, object]]:
    return [
        feature
        for feature in features
        if boundary.covers(parse_boundary(feature.get("geometry")).point_on_surface)
    ]


def quote_ogr_value(value: str) -> str:
    escaped_value = value.replace("'", "''")
    return f"'{escaped_value}'"


def parse_other_tags(value: object) -> dict[str, object]:
    """Keep GDAL's hstore payload structured; empty payloads are harmless."""
    if not isinstance(value, str) or not value:
        return {}
    import re

    return {
        key: raw.replace('\\"', '"').replace("\\\\", "\\")
        for key, raw in re.findall(r'"((?:\\.|[^"])*)"=>"((?:\\.|[^"])*)"', value)
    }


def download_source(source_object_key: str) -> bytes:
    if not settings.OBJECT_STORAGE_BUCKET:
        raise OsmImportConfigurationError(
            "Configure OBJECT_STORAGE_BUCKET for OSM imports."
        )

    try:
        response = get_cache_storage_client().get_object(
            Bucket=settings.OBJECT_STORAGE_BUCKET,
            Key=source_object_key,
        )
        body = response["Body"]
        try:
            return bytes(body.read())
        finally:
            body.close()
    except OsmImportConfigurationError:
        raise
    except Exception as exc:
        raise OsmImportSourceUnavailable(
            f"Could not read OSM source object {source_object_key!r}."
        ) from exc


def parse_source(source_bytes: bytes) -> list[ImportedArea]:
    try:
        source = json.loads(source_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OsmImportConfigurationError("The source is not valid GeoJSON.") from exc

    if source.get("type") != "FeatureCollection" or not isinstance(
        source.get("features"), list
    ):
        raise OsmImportConfigurationError(
            "The source must be a GeoJSON FeatureCollection."
        )

    areas = [parse_feature(feature) for feature in source["features"]]
    identities = {(area.osm_element_type, area.source_id) for area in areas}
    if len(identities) != len(areas):
        raise OsmImportConfigurationError(
            "The source contains duplicate OSM identities."
        )
    return areas


def parse_feature(feature: object) -> ImportedArea:
    if not isinstance(feature, dict) or feature.get("type") != "Feature":
        raise OsmImportConfigurationError(
            "Every source item must be a GeoJSON Feature."
        )
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        raise OsmImportConfigurationError("Every source feature needs properties.")

    country_code = required_string(properties, "country_code").upper()
    name = required_string(properties, "name")
    area_type = required_string(properties, "area_type")
    valid_area_types = {choice for choice, _label in ServiceArea.AreaType.choices}
    if area_type not in valid_area_types:
        raise OsmImportConfigurationError(f"Unsupported area_type {area_type!r}.")

    osm_element_type = required_string(properties, "osm_element_type")
    valid_element_types = {
        choice for choice, _label in ServiceArea.OsmElementType.choices
    }
    if osm_element_type not in valid_element_types:
        raise OsmImportConfigurationError(
            f"Unsupported osm_element_type {osm_element_type!r}."
        )

    source_id = required_string(properties, "source_id")
    boundary = parse_boundary(feature.get("geometry"))
    osm_tags = properties.get("osm_tags", {})
    if not isinstance(osm_tags, dict):
        raise OsmImportConfigurationError("osm_tags must be an object.")

    parent_identity = parse_parent_identity(properties)
    return ImportedArea(
        country_code=country_code,
        name=name,
        slug=slugify(str(properties.get("slug") or name)),
        area_type=area_type,
        boundary=boundary,
        source_id=source_id,
        osm_element_type=osm_element_type,
        osm_admin_level=optional_positive_int(properties, "osm_admin_level"),
        osm_tags={str(key): value for key, value in osm_tags.items()},
        population=optional_positive_int(properties, "population"),
        timezone=str(properties.get("timezone", "")),
        parent_identity=parent_identity,
    )


def parse_boundary(geometry: object) -> MultiPolygon:
    if not isinstance(geometry, dict):
        raise OsmImportConfigurationError("Every source feature needs a geometry.")
    try:
        parsed_geometry = GEOSGeometry(json.dumps(geometry), srid=4326)
    except (GEOSException, TypeError, ValueError) as exc:
        raise OsmImportConfigurationError("A source geometry is invalid.") from exc

    if isinstance(parsed_geometry, Polygon):
        return MultiPolygon(parsed_geometry, srid=4326)
    if isinstance(parsed_geometry, MultiPolygon):
        return parsed_geometry
    raise OsmImportConfigurationError("Administrative boundaries must be polygons.")


def create_service_areas(
    osm_import_run: OsmImportRun,
    areas: list[ImportedArea],
) -> list[ServiceArea]:
    countries = {
        country.code: country
        for country in Country.objects.filter(
            code__in={area.country_code for area in areas}
        )
    }
    missing_countries = sorted({area.country_code for area in areas} - countries.keys())
    if missing_countries:
        raise OsmImportConfigurationError(
            f"No Country exists for: {', '.join(missing_countries)}."
        )

    created_by_identity: dict[tuple[str, str], ServiceArea] = {}
    created_areas: list[ServiceArea] = []
    for area in areas:
        bbox = area.boundary.envelope
        if not isinstance(bbox, Polygon):
            raise OsmImportConfigurationError(
                "A source boundary has no polygon envelope."
            )
        service_area = ServiceArea.objects.create(
            import_run=osm_import_run,
            country=countries[area.country_code],
            slug=available_slug(
                country=countries[area.country_code],
                base_slug=area.slug,
                run_id=osm_import_run.pk,
            ),
            name=area.name,
            area_type=area.area_type,
            center=area.boundary.point_on_surface,
            boundary=area.boundary,
            bbox=bbox,
            population=area.population,
            timezone=area.timezone,
            source=ServiceArea.SourceType.OSM,
            source_id=area.source_id,
            osm_element_type=area.osm_element_type,
            osm_admin_level=area.osm_admin_level,
            osm_tags=area.osm_tags,
        )
        created_by_identity[(area.osm_element_type, area.source_id)] = service_area
        created_areas.append(service_area)

    for area, service_area in zip(areas, created_areas, strict=True):
        if area.parent_identity is None:
            continue
        parent = created_by_identity.get(area.parent_identity)
        if parent is None:
            raise OsmImportConfigurationError(
                f"Parent OSM area {area.parent_identity!r} is not in this import."
            )
        if parent.country != service_area.country:
            raise OsmImportConfigurationError(
                "A service area's parent must share its country."
            )
        service_area.parent = parent
        service_area.save(update_fields=["parent"])

    return created_areas


def available_slug(*, country: Country, base_slug: str, run_id: int | None) -> str:
    if not base_slug:
        raise OsmImportConfigurationError("A source feature needs a slug or name.")

    max_length = ServiceArea._meta.get_field("slug").max_length
    if max_length is None:
        raise OsmImportConfigurationError("Service area slugs need a maximum length.")

    base_slug = truncate_slug(base_slug, max_length)
    candidate = base_slug
    suffix = f"-import-{run_id}" if run_id is not None else "-import"
    sequence = 1
    while ServiceArea.objects.filter(country=country, slug=candidate).exists():
        numbered_suffix = suffix if sequence == 1 else f"{suffix}-{sequence}"
        candidate = f"{truncate_slug(base_slug, max_length - len(numbered_suffix))}{numbered_suffix}"
        sequence += 1
    return candidate


def truncate_slug(value: str, max_length: int) -> str:
    truncated = value[:max_length].rstrip("-")
    if not truncated:
        raise OsmImportConfigurationError("A source feature needs a usable slug.")
    return truncated


def required_string(properties: dict[str, object], key: str) -> str:
    value = properties.get(key)
    if not isinstance(value, str) or not value.strip():
        raise OsmImportConfigurationError(f"A source feature needs a non-empty {key}.")
    return value.strip()


def optional_positive_int(properties: dict[str, object], key: str) -> int | None:
    value = properties.get(key)
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise OsmImportConfigurationError(f"{key} must be a positive integer.")
    if not isinstance(value, int | str):
        raise OsmImportConfigurationError(f"{key} must be a positive integer.")
    try:
        parsed_value = int(value)
    except (TypeError, ValueError) as exc:
        raise OsmImportConfigurationError(f"{key} must be a positive integer.") from exc
    if parsed_value < 0:
        raise OsmImportConfigurationError(f"{key} must be a positive integer.")
    return parsed_value


def parse_parent_identity(
    properties: dict[str, object],
) -> tuple[str, str] | None:
    source_id = properties.get("parent_source_id")
    element_type = properties.get("parent_osm_element_type")
    if source_id in (None, "") and element_type in (None, ""):
        return None
    if not isinstance(source_id, str) or not isinstance(element_type, str):
        raise OsmImportConfigurationError(
            "parent_source_id and parent_osm_element_type must be supplied together."
        )
    return (element_type, source_id)


def fail_osm_import(osm_import_run: OsmImportRun, error: Exception) -> None:
    osm_import_run.status = OsmImportRun.Status.FAILED
    osm_import_run.is_active = False
    osm_import_run.finished_at = timezone.now()
    osm_import_run.current_stage = "Failed"
    osm_import_run.error_summary = str(error)
    osm_import_run.save(
        update_fields=[
            "status",
            "is_active",
            "finished_at",
            "current_stage",
            "error_summary",
        ]
    )
