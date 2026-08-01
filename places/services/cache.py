import hashlib
from collections.abc import Mapping
from typing import Any, cast

from django.conf import settings
from django.core.cache import cache


def get_payload(
    query_params: Mapping[str, Any],
) -> dict[str, Any] | None:
    if settings.CACHE_TIMEOUT_IN_SECS == 0:
        return None

    cached_payload = cache.get(build_cache_key(query_params))

    if cached_payload is None:
        return None

    return cast(dict[str, Any], cached_payload)


def set_payload(
    query_params: Mapping[str, Any],
    payload: dict[str, Any],
) -> None:
    if settings.CACHE_TIMEOUT_IN_SECS == 0:
        return

    cache.set(
        build_cache_key(query_params),
        payload,
        settings.CACHE_TIMEOUT_IN_SECS,
    )


def build_cache_key(query_params: Mapping[str, Any]) -> str:
    cache_key = (
        "open-street-map-"
        f"{query_params['lat']}-"
        f"{query_params['lng']}-"
        f"{query_params['search_radius']}-"
        f"{query_params.get('category', '')}-"
        f"{query_params.get('category_group', '')}"
    )

    return hashlib.sha1(cache_key.encode("utf-8")).hexdigest()
