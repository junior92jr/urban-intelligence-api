import pytest
from chainmock import mocker

from geo.models import ServiceArea, build_point
from places.models import AreaScan, DataImport, DiscoveredPlace
from places.services import discovery
from places.services.mappers import OpenStreetMapApiResponse

pytestmark = pytest.mark.django_db


def test_create_area_scan_keeps_category_and_category_group():
    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")

    scan = discovery.create_area_scan(
        service_area=service_area,
        latitude=50.1109,
        longitude=8.6821,
        radius=500,
        user_id=None,
        category="restaurant",
    )

    assert scan.category == "restaurant"
    assert scan.category_group == "food"
    assert scan.latitude == 50.1109
    assert scan.longitude == 8.6821


def test_create_area_scan_keeps_requested_category_group():
    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")

    scan = discovery.create_area_scan(
        service_area=service_area,
        latitude=50.1109,
        longitude=8.6821,
        radius=500,
        user_id=None,
        category_group="mobility",
    )

    assert scan.category == ""
    assert scan.category_group == "mobility"


def test_upsert_discovered_places_creates_persistent_places():
    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")
    response = OpenStreetMapApiResponse.from_api_response(
        {
            "elements": [
                {
                    "type": "node",
                    "id": 1,
                    "lat": 50.1109,
                    "lon": 8.6821,
                    "tags": {
                        "amenity": "restaurant",
                        "name": "Good Food",
                    },
                },
            ],
        }
    )

    result_count = discovery.upsert_discovered_places(
        service_area=service_area,
        places=response.places,
    )
    place = DiscoveredPlace.objects.get()

    assert result_count == 1
    assert place.name == "Good Food"
    assert place.category == "restaurant"
    assert place.category_group == "food"
    assert place.latitude == 50.1109
    assert place.longitude == 8.6821


def test_nearby_places_filters_by_distance_and_category():
    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")
    DiscoveredPlace.objects.create(
        service_area=service_area,
        osm_uid="osm-node-1",
        osm_id=1,
        osm_type="node",
        name="Nearby Cafe",
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
        name="Nearby Parking",
        category="parking",
        category_name="Parking",
        category_group="mobility",
        location=build_point(latitude=50.1109, longitude=8.6821),
    )

    places = list(
        discovery.nearby_places(
            service_area=service_area,
            latitude=50.1109,
            longitude=8.6821,
            radius=500,
            category="cafe",
        )
    )

    assert [place.name for place in places] == ["Nearby Cafe"]


def test_nearby_places_filters_by_category_group():
    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")
    DiscoveredPlace.objects.create(
        service_area=service_area,
        osm_uid="osm-node-1",
        osm_id=1,
        osm_type="node",
        name="Nearby Cafe",
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
        name="Nearby Parking",
        category="parking",
        category_name="Parking",
        category_group="mobility",
        location=build_point(latitude=50.1109, longitude=8.6821),
    )

    places = list(
        discovery.nearby_places(
            service_area=service_area,
            latitude=50.1109,
            longitude=8.6821,
            radius=500,
            category_group="mobility",
        )
    )

    assert [place.name for place in places] == ["Nearby Parking"]


def test_run_scan_updates_scan_status_and_persists_results():
    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")
    scan = AreaScan.objects.create(
        service_area=service_area,
        center=build_point(latitude=50.1109, longitude=8.6821),
        radius=500,
        category="restaurant",
        category_group="food",
    )
    response = OpenStreetMapApiResponse.from_api_response(
        {
            "elements": [
                {
                    "type": "node",
                    "id": 1,
                    "lat": 50.1109,
                    "lon": 8.6821,
                    "tags": {
                        "amenity": "restaurant",
                        "name": "Good Food",
                    },
                },
            ],
        }
    )
    mocker(discovery).mock("search_places_by_location").called_once_with(
        {
            "lat": 50.1109,
            "lng": 8.6821,
            "search_radius": 500,
            "category": "restaurant",
        }
    ).return_value(response)

    result_count = discovery.run_scan(scan)
    scan.refresh_from_db()

    assert result_count == 1
    assert scan.status == AreaScan.Status.COMPLETED
    assert scan.result_count == 1
    assert DiscoveredPlace.objects.filter(name="Good Food").exists()


def test_run_data_import_updates_status_and_persists_requested_group_results():
    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")
    data_import = DataImport.objects.create(
        service_area=service_area,
        category_group="food",
        radius=8000,
    )
    response = OpenStreetMapApiResponse.from_api_response(
        {
            "elements": [
                {
                    "type": "node",
                    "id": 1,
                    "lat": 50.1109,
                    "lon": 8.6821,
                    "tags": {
                        "amenity": "restaurant",
                        "name": "Good Food",
                    },
                },
                {
                    "type": "node",
                    "id": 2,
                    "lat": 50.111,
                    "lon": 8.683,
                    "tags": {
                        "amenity": "parking",
                        "name": "Parking",
                    },
                },
            ],
        }
    )
    mocker(discovery).mock("search_places_by_location").called_once_with(
        {
            "lat": service_area.latitude,
            "lng": service_area.longitude,
            "search_radius": 8000,
            "category_group": "food",
        }
    ).return_value(response)

    result_count = discovery.run_data_import(data_import)
    data_import.refresh_from_db()

    assert result_count == 1
    assert data_import.status == DataImport.Status.COMPLETED
    assert data_import.result_count == 1
    assert DiscoveredPlace.objects.filter(name="Good Food").exists()
    assert not DiscoveredPlace.objects.filter(name="Parking").exists()


def test_place_matches_scan_prefers_exact_category_over_group():
    scan = AreaScan(category="restaurant", category_group="food")
    response = OpenStreetMapApiResponse.from_api_response(
        {
            "elements": [
                {
                    "type": "node",
                    "id": 1,
                    "lat": 50.1109,
                    "lon": 8.6821,
                    "tags": {
                        "amenity": "cafe",
                        "name": "Cafe",
                    },
                },
            ],
        }
    )

    assert not discovery.place_matches_scan(response.places[0], scan)
