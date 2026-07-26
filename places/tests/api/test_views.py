import pytest
from chainmock import mocker
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from places import views
from places.services.mappers import OpenStreetMapApiResponse

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_api_client(api_client):
    user = User.objects.create_user(
        email="places@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    api_client.force_authenticate(user=user)
    return api_client


def test_places_requires_authentication(api_client):
    response = api_client.get(
        "/api/v1/places/",
        {
            "lat": "50.1101038",
            "lng": "8.6771586",
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_places_returns_mapped_open_street_map_response(authenticated_api_client):
    query_params = {
        "lat": 50.1101038,
        "lng": 8.6771586,
        "search_radius": 500,
    }
    service_response = OpenStreetMapApiResponse.from_api_response(
        {
            "version": 0.6,
            "generator": "Overpass API",
            "elements": [
                {
                    "type": "node",
                    "id": 331124761,
                    "lat": 51.9322712,
                    "lon": 6.9442418,
                    "tags": {
                        "historic": "wayside_shrine",
                        "name": "Heiliger Ludgerus",
                    },
                },
            ],
        }
    )
    mocker(views).mock("search_places_by_location").called_once_with(
        query_params
    ).return_value(service_response)

    response = authenticated_api_client.get(
        "/api/v1/places/",
        {
            "lat": "50.1101038",
            "lng": "8.6771586",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "places": [
            {
                "osm_id": 331124761,
                "osm_type": "node",
                "name": "Heiliger Ludgerus",
                "latitude": 51.9322712,
                "longitude": 6.9442418,
                "category": "wayside-shrine",
                "category_name": "Wayside Shrine",
                "osm_uid": "osm-node-331124761",
            },
        ],
    }


def test_places_passes_optional_radius_to_search_service(authenticated_api_client):
    query_params = {
        "lat": 50.1101038,
        "lng": 8.6771586,
        "search_radius": 250,
    }
    service_response = OpenStreetMapApiResponse.from_api_response(
        {
            "elements": [],
        }
    )
    mocker(views).mock("search_places_by_location").called_once_with(
        query_params
    ).return_value(service_response)

    response = authenticated_api_client.get(
        "/api/v1/places/",
        {
            "lat": "50.1101038",
            "lng": "8.6771586",
            "search_radius": "250",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"places": []}


def test_places_returns_bad_request_for_invalid_query_params(authenticated_api_client):
    mocker(views).mock("search_places_by_location").not_called()

    response = authenticated_api_client.get(
        "/api/v1/places/",
        {
            "lat": "not-a-float",
            "lng": "8.6771586",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "lat" in response.json()


def test_places_passes_optional_category_to_search_service(authenticated_api_client):
    query_params = {
        "lat": 50.1101038,
        "lng": 8.6771586,
        "search_radius": 500,
        "category": "parking",
    }
    service_response = OpenStreetMapApiResponse.from_api_response(
        {
            "elements": [],
        }
    )
    mocker(views).mock("search_places_by_location").called_once_with(
        query_params
    ).return_value(service_response)

    response = authenticated_api_client.get(
        "/api/v1/places/",
        {
            "lat": "50.1101038",
            "lng": "8.6771586",
            "category": "parking",
        },
    )

    assert response.status_code == status.HTTP_200_OK


def test_categories_endpoint_returns_known_categories(api_client):
    response = api_client.get("/api/v1/categories/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()[3] == {
        "slug": "parking",
        "name": "Parking",
    }
