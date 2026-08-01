from django.core.cache import cache

from places.services import cache as open_street_map_cache


def test_build_key_uses_location_and_radius():
    first_key = open_street_map_cache.build_cache_key(
        {
            "lat": 50.1101038,
            "lng": 8.6771586,
            "search_radius": 500,
        }
    )
    second_key = open_street_map_cache.build_cache_key(
        {
            "lat": 50.1101038,
            "lng": 8.6771586,
            "search_radius": 1000,
        }
    )

    assert first_key != second_key


def test_build_key_uses_category_filters():
    first_key = open_street_map_cache.build_cache_key(
        {
            "lat": 50.1101038,
            "lng": 8.6771586,
            "search_radius": 500,
            "category": "restaurant",
        }
    )
    second_key = open_street_map_cache.build_cache_key(
        {
            "lat": 50.1101038,
            "lng": 8.6771586,
            "search_radius": 500,
            "category_group": "food",
        }
    )

    assert first_key != second_key


def test_get_payload_returns_none_when_cache_is_disabled(settings):
    settings.CACHE_TIMEOUT_IN_SECS = 0
    query_params = {
        "lat": 50.1101038,
        "lng": 8.6771586,
        "search_radius": 1000,
    }
    cache.set(
        open_street_map_cache.build_cache_key(query_params),
        {"elements": []},
    )

    assert open_street_map_cache.get_payload(query_params) is None


def test_set_and_get_payload(settings):
    settings.CACHE_TIMEOUT_IN_SECS = 86400
    query_params = {
        "lat": 50.1101038,
        "lng": 8.6771586,
        "search_radius": 1000,
    }
    payload = {"elements": [{"type": "node", "id": 1}]}

    open_street_map_cache.set_payload(query_params, payload)

    assert open_street_map_cache.get_payload(query_params) == payload
