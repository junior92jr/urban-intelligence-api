import pytest
from chainmock import mocker
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from places import views
from places.models import AreaScan, DiscoveredPlace
from places.services.mappers import OpenStreetMapApiResponse
from user_places.models import SearchHistory

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


def test_places_records_search_history(authenticated_api_client):
    service_response = OpenStreetMapApiResponse.from_api_response(
        {
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
    mocker(views).mock("search_places_by_location").return_value(service_response)

    response = authenticated_api_client.get(
        "/api/v1/places/",
        {
            "lat": "50.1101038",
            "lng": "8.6771586",
            "category": "parking",
        },
    )

    history = SearchHistory.objects.get()
    assert response.status_code == status.HTTP_200_OK
    assert history.latitude == 50.1101038
    assert history.longitude == 8.6771586
    assert history.search_radius == 500
    assert history.category == "parking"
    assert history.result_count == 1


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
        "group": "mobility",
    }


def test_nearby_places_returns_persisted_places(authenticated_api_client):
    from accounts.models import UserProfile
    from geo.models import ServiceArea, build_point

    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")
    UserProfile.objects.create(
        user=User.objects.get(email="places@example.com"),
        service_area=service_area,
    )
    DiscoveredPlace.objects.create(
        service_area=service_area,
        osm_uid="osm-node-1",
        osm_id=1,
        osm_type="node",
        name="Persisted Cafe",
        category="cafe",
        category_name="Cafe",
        category_group="food",
        location=build_point(latitude=50.1109, longitude=8.6821),
    )

    response = authenticated_api_client.get(
        "/api/v1/places/nearby/",
        {
            "lat": "50.1109",
            "lng": "8.6821",
            "search_radius": "500",
            "category": "cafe",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["places"][0]["name"] == "Persisted Cafe"
    assert response.json()["places"][0]["distance_meters"] == 0


def test_nearby_places_is_scoped_to_the_users_service_area(
    authenticated_api_client,
):
    from accounts.models import UserProfile
    from geo.models import ServiceArea, build_point

    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")
    other_service_area = ServiceArea.objects.create(
        country=service_area.country,
        slug="frankfurt-nord",
        name="Frankfurt Nord",
        center=build_point(latitude=50.0954, longitude=8.6809),
    )
    UserProfile.objects.create(
        user=User.objects.get(email="places@example.com"),
        service_area=service_area,
    )
    place_defaults = {
        "osm_uid": "osm-node-2706991161",
        "osm_id": 2706991161,
        "osm_type": "node",
        "name": "Ristorante Colosseo",
        "category": "restaurant",
        "category_name": "Restaurant",
        "category_group": "food",
        "location": build_point(latitude=50.0953931, longitude=8.681116),
    }
    DiscoveredPlace.objects.create(service_area=service_area, **place_defaults)
    DiscoveredPlace.objects.create(
        service_area=other_service_area,
        **place_defaults,
    )

    response = authenticated_api_client.get(
        "/api/v1/places/nearby/",
        {
            "lat": "50.0954",
            "lng": "8.6809",
            "search_radius": "500",
            "category": "restaurant",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert [place["osm_uid"] for place in response.json()["places"]] == [
        "osm-node-2706991161"
    ]


def test_nearby_places_filters_persisted_places_by_category_group(
    authenticated_api_client,
):
    from accounts.models import UserProfile
    from geo.models import ServiceArea, build_point

    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")
    UserProfile.objects.create(
        user=User.objects.get(email="places@example.com"),
        service_area=service_area,
    )
    DiscoveredPlace.objects.create(
        service_area=service_area,
        osm_uid="osm-node-1",
        osm_id=1,
        osm_type="node",
        name="Persisted Cafe",
        category="cafe",
        category_name="Cafe",
        category_group="food",
        location=build_point(latitude=50.1109, longitude=8.6821),
    )
    DiscoveredPlace.objects.create(
        service_area=service_area,
        osm_uid="osm-node-2",
        osm_id=2,
        osm_type="node",
        name="Persisted Parking",
        category="parking",
        category_name="Parking",
        category_group="mobility",
        location=build_point(latitude=50.1109, longitude=8.6821),
    )

    response = authenticated_api_client.get(
        "/api/v1/places/nearby/",
        {
            "lat": "50.1109",
            "lng": "8.6821",
            "search_radius": "500",
            "category_group": "mobility",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert [place["name"] for place in response.json()["places"]] == [
        "Persisted Parking"
    ]


def test_area_scan_endpoint_creates_background_scan(authenticated_api_client):
    from accounts.models import UserProfile
    from geo.models import ServiceArea

    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")
    user = User.objects.get(email="places@example.com")
    UserProfile.objects.create(user=user, service_area=service_area)
    mocker(views.run_area_scan).mock("delay").called_once()

    response = authenticated_api_client.post(
        "/api/v1/places/area-scans/",
        {
            "lat": "50.1109",
            "lng": "8.6821",
            "search_radius": "500",
            "category": "restaurant",
        },
        format="json",
    )
    scan = AreaScan.objects.get()

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["status"] == "pending"
    assert response.json()["category"] == "restaurant"
    assert scan.category_group == "food"
    assert scan.category == "restaurant"


def test_area_scan_endpoint_creates_background_group_scan(authenticated_api_client):
    from accounts.models import UserProfile
    from geo.models import ServiceArea

    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")
    user = User.objects.get(email="places@example.com")
    UserProfile.objects.create(user=user, service_area=service_area)
    mocker(views.run_area_scan).mock("delay").called_once()

    response = authenticated_api_client.post(
        "/api/v1/places/area-scans/",
        {
            "lat": "50.1109",
            "lng": "8.6821",
            "search_radius": "500",
            "category_group": "mobility",
        },
        format="json",
    )
    scan = AreaScan.objects.get()

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["status"] == "pending"
    assert response.json()["category"] == ""
    assert response.json()["category_group"] == "mobility"
    assert scan.category_group == "mobility"
    assert scan.category == ""
