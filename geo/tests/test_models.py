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


def test_service_area_string_includes_country_code() -> None:
    berlin = ServiceArea.objects.get(slug="berlin")

    assert str(berlin) == "Berlin, DE"
