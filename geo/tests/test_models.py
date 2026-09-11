import pytest
from django.db import IntegrityError, transaction

from geo.models import Country, OsmImportRun, ServiceArea, build_point

pytestmark = pytest.mark.django_db


def test_germany_service_areas_are_seeded() -> None:
    germany = Country.objects.get(code="DE")
    frankfurt = ServiceArea.objects.get(slug="frankfurt-am-main")

    assert germany.name == "Germany"
    assert germany.currency == "EUR"
    assert frankfurt.country == germany
    assert frankfurt.name == "Frankfurt am Main"
    assert frankfurt.latitude == 50.1109
    assert frankfurt.longitude == 8.6821


def test_germany_service_areas_are_seeded_with_official_boundaries() -> None:
    service_areas = ServiceArea.objects.filter(country__code="DE")

    assert service_areas.count() == 10
    for service_area in service_areas:
        assert service_area.boundary is not None
        assert service_area.boundary.srid == 4326
        assert service_area.boundary.valid
        assert service_area.bbox is not None
        assert service_area.bbox.srid == 4326
        assert service_area.bbox.contains(service_area.center)
        boundary_config = service_area.data_config["boundary"]
        assert boundary_config["dataset"] == "BKG VG250"
        assert boundary_config["license"] == "dl-de/by-2-0"
        assert boundary_config["reference_date"] == "2026-01-01"
        assert boundary_config["municipality_key"]
        assert boundary_config["source_name"]


def test_service_area_string_includes_country_code() -> None:
    berlin = ServiceArea.objects.get(slug="berlin")

    assert str(berlin) == "Berlin, DE"


def test_active_service_areas_include_only_the_active_osm_dataset() -> None:
    germany = Country.objects.get(code="DE")
    active_run = OsmImportRun.objects.create(
        source_object_key="imports/de-active.osm.pbf",
        city_slug="berlin",
        status=OsmImportRun.Status.SUCCEEDED,
        is_active=True,
    )
    inactive_run = OsmImportRun.objects.create(
        source_object_key="imports/de-inactive.osm.pbf",
        status=OsmImportRun.Status.SUPERSEDED,
    )
    active_area = ServiceArea.objects.create(
        country=germany,
        import_run=active_run,
        slug="active-osm-area",
        name="Active OSM area",
        source=ServiceArea.SourceType.OSM,
        source_id="62400",
        osm_element_type=ServiceArea.OsmElementType.RELATION,
        area_type=ServiceArea.AreaType.CITY,
        center=build_point(latitude=50.0, longitude=8.0),
    )
    inactive_area = ServiceArea.objects.create(
        country=germany,
        import_run=inactive_run,
        slug="inactive-osm-area",
        name="Inactive OSM area",
        source=ServiceArea.SourceType.OSM,
        source_id="62400",
        osm_element_type=ServiceArea.OsmElementType.RELATION,
        area_type=ServiceArea.AreaType.CITY,
        center=build_point(latitude=51.0, longitude=8.0),
    )

    active_ids = set(ServiceArea.objects.active().values_list("id", flat=True))

    assert active_area.pk in active_ids
    assert inactive_area.pk not in active_ids
    # Legacy rows are visible only until an active imported dataset replaces them.
    assert ServiceArea.objects.get(slug="berlin").pk not in active_ids


def test_only_one_active_osm_import_run_is_allowed_per_city() -> None:
    OsmImportRun.objects.create(
        source_object_key="imports/berlin-a.osm.pbf",
        city_slug="berlin",
        status=OsmImportRun.Status.SUCCEEDED,
        is_active=True,
    )

    with transaction.atomic(), pytest.raises(IntegrityError):
        OsmImportRun.objects.create(
            source_object_key="imports/berlin-b.osm.pbf",
            city_slug="berlin",
            status=OsmImportRun.Status.SUCCEEDED,
            is_active=True,
        )


def test_active_osm_import_runs_are_allowed_for_different_cities() -> None:
    for city_slug in ("hamburg", "munich"):
        OsmImportRun.objects.create(
            source_object_key=f"imports/{city_slug}.osm.pbf",
            city_slug=city_slug,
            status=OsmImportRun.Status.SUCCEEDED,
            is_active=True,
        )
