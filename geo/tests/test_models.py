import pytest

from geo.models import Country, ServiceArea

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
