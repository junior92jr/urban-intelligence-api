import httpx
import pytest
from chainmock import mocker

from places.models import PlaceCategory
from places.services import cache as open_street_map_cache
from places.services import open_street_map
from places.services.open_street_map import (
    OpenStreetMapResourceUnavailable,
    PlaceQueryParams,
)

pytestmark = pytest.mark.django_db


def test_build_request_payload_uses_radius_parameter():
    payload = open_street_map.build_request_payload(
        {
            "lat": 50.1101038,
            "lng": 8.6771586,
            "search_radius": 1000,
        }
    )

    assert "around:1000,50.1101038,8.6771586" in payload["data"]
    assert '["amenity"="parking"]' in payload["data"]
    assert '["historic"="wayside_shrine"]' not in payload["data"]


def test_build_request_payload_uses_request_radius():
    payload = open_street_map.build_request_payload(
        {
            "lat": 50.1101038,
            "lng": 8.6771586,
            "search_radius": 250,
        }
    )

    assert "around:250,50.1101038,8.6771586" in payload["data"]


def test_build_request_payload_uses_only_requested_category():
    payload = open_street_map.build_request_payload(
        {
            "lat": 50.1101038,
            "lng": 8.6771586,
            "search_radius": 250,
            "category": "bar",
        }
    )

    assert '["amenity"="bar"]' in payload["data"]
    assert '["amenity"="parking"]' not in payload["data"]
    assert '["tourism"="museum"]' not in payload["data"]


def test_build_request_payload_raises_when_no_categories_are_active():
    PlaceCategory.objects.update(is_active=False)

    with pytest.raises(OpenStreetMapResourceUnavailable):
        open_street_map.build_request_payload(
            {
                "lat": 50.1101038,
                "lng": 8.6771586,
                "search_radius": 250,
            }
        )


def test_headers_uses_configured_user_agent(settings):
    settings.OPEN_STREET_MAP_USER_AGENT = "city-guide-tests"

    assert open_street_map.headers() == {
        "Accept": "application/json",
        "User-Agent": "city-guide-tests",
    }


def test_request_places_calls_overpass(settings):
    settings.OPEN_STREET_MAP_OVERPASS_URL = "https://overpass.test/api"
    settings.OPEN_STREET_MAP_USER_AGENT = "city-guide-tests"
    response = httpx.Response(
        httpx.codes.OK,
        json={"elements": []},
        request=httpx.Request("GET", "https://overpass.test/api"),
    )

    mocker(open_street_map.httpx).mock("get").called_once().return_value(response)

    assert (
        open_street_map.request_places(
            {
                "lat": 50.1101038,
                "lng": 8.6771586,
                "search_radius": 1000,
            }
        )
        == response
    )


def test_request_places_retries_request_errors(settings):
    settings.OPEN_STREET_MAP_OVERPASS_URL = "https://overpass.test/api"
    settings.OPEN_STREET_MAP_MAX_RETRIES = 1
    request = httpx.Request("GET", "https://overpass.test/api")
    response = httpx.Response(
        httpx.codes.OK,
        json={"elements": []},
        request=request,
    )
    mocker(open_street_map).mock("wait_before_retry").called_once_with(1)
    mocker(open_street_map.httpx).mock("get").side_effect(
        [httpx.ReadTimeout("read timed out", request=request), response]
    )

    assert (
        open_street_map.request_places(
            {
                "lat": 50.1101038,
                "lng": 8.6771586,
                "search_radius": 1000,
            }
        )
        == response
    )


def test_request_places_retries_retryable_status_codes(settings):
    settings.OPEN_STREET_MAP_OVERPASS_URL = "https://overpass.test/api"
    settings.OPEN_STREET_MAP_MAX_RETRIES = 1
    request = httpx.Request("GET", "https://overpass.test/api")
    unavailable_response = httpx.Response(
        httpx.codes.GATEWAY_TIMEOUT,
        text="server busy",
        request=request,
    )
    response = httpx.Response(
        httpx.codes.OK,
        json={"elements": []},
        request=request,
    )
    mocker(open_street_map).mock("wait_before_retry").called_once_with(1)
    mocker(open_street_map.httpx).mock("get").side_effect(
        [unavailable_response, response]
    )

    assert (
        open_street_map.request_places(
            {
                "lat": 50.1101038,
                "lng": 8.6771586,
                "search_radius": 1000,
            }
        )
        == response
    )


def test_request_places_raises_service_unavailable_for_request_errors():
    request = httpx.Request("GET", "https://overpass.test/api")
    mocker(open_street_map.httpx).mock("get").side_effect(
        httpx.ConnectError("connection failed", request=request)
    )

    with pytest.raises(OpenStreetMapResourceUnavailable):
        open_street_map.request_places(
            {
                "lat": 50.1101038,
                "lng": 8.6771586,
                "search_radius": 1000,
            }
        )


def test_fetch_places_payload_returns_cached_payload():
    query_params: PlaceQueryParams = {
        "lat": 50.1101038,
        "lng": 8.6771586,
        "search_radius": 1000,
    }
    payload = {"elements": []}
    mocker(open_street_map_cache).mock("get_payload").called_once_with(
        query_params
    ).return_value(payload)
    mocker(open_street_map).mock("request_places").not_called()

    assert open_street_map.fetch_places_payload(query_params) == payload


def test_fetch_places_payload_caches_successful_payload():
    query_params: PlaceQueryParams = {
        "lat": 50.1101038,
        "lng": 8.6771586,
        "search_radius": 1000,
    }
    payload = {"elements": []}
    response = httpx.Response(
        httpx.codes.OK,
        json=payload,
        request=httpx.Request("GET", "https://overpass.test/api"),
    )
    mocker(open_street_map_cache).mock("get_payload").return_value(None)
    mocker(open_street_map).mock("request_places").return_value(response)
    mocker(open_street_map_cache).mock("set_payload").called_once_with(
        query_params,
        payload,
    )

    assert open_street_map.fetch_places_payload(query_params) == payload


def test_fetch_places_payload_raises_service_unavailable_for_error_status():
    response = httpx.Response(
        httpx.codes.INTERNAL_SERVER_ERROR,
        json={"remark": "runtime error"},
        request=httpx.Request("GET", "https://overpass.test/api"),
    )
    mocker(open_street_map_cache).mock("get_payload").return_value(None)
    mocker(open_street_map).mock("request_places").return_value(response)

    with pytest.raises(OpenStreetMapResourceUnavailable):
        open_street_map.fetch_places_payload(
            {
                "lat": 50.1101038,
                "lng": 8.6771586,
                "search_radius": 1000,
            }
        )


def test_fetch_places_payload_raises_service_unavailable_for_non_object_json():
    response = httpx.Response(
        httpx.codes.OK,
        json=[],
        request=httpx.Request("GET", "https://overpass.test/api"),
    )
    mocker(open_street_map_cache).mock("get_payload").return_value(None)
    mocker(open_street_map).mock("request_places").return_value(response)

    with pytest.raises(OpenStreetMapResourceUnavailable):
        open_street_map.fetch_places_payload(
            {
                "lat": 50.1101038,
                "lng": 8.6771586,
                "search_radius": 1000,
            }
        )
