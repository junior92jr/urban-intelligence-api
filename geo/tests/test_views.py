import pytest
from rest_framework import status
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def test_countries_endpoint_returns_active_countries(api_client: APIClient) -> None:
    response = api_client.get("/api/v1/geo/countries/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        {
            "id": response.json()[0]["id"],
            "code": "DE",
            "name": "Germany",
            "default_language": "de",
            "timezone": "Europe/Berlin",
            "currency": "EUR",
        },
    ]


def test_service_areas_endpoint_returns_germany_cities(api_client: APIClient) -> None:
    response = api_client.get("/api/v1/geo/service-areas/", {"country": "DE"})
    payload = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(payload) == 10
    assert payload[0]["slug"] == "berlin"
    assert payload[0]["country"]["code"] == "DE"
    assert payload[0]["center"] == {"lat": 52.52, "lng": 13.405}


def test_service_areas_endpoint_filters_unknown_country(api_client: APIClient) -> None:
    response = api_client.get("/api/v1/geo/service-areas/", {"country": "ES"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []
