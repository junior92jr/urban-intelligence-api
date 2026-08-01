import logging
import time
from typing import Any, NotRequired, TypedDict

import httpx
from django.conf import settings
from rest_framework.exceptions import APIException

from . import cache
from .categories import (
    get_default_osm_category_tags,
    get_osm_category_tags_for_group,
    get_osm_category_tags_for_slug,
)

RETRYABLE_STATUS_CODES = {
    httpx.codes.TOO_MANY_REQUESTS,
    httpx.codes.BAD_GATEWAY,
    httpx.codes.SERVICE_UNAVAILABLE,
    httpx.codes.GATEWAY_TIMEOUT,
}
logger = logging.getLogger(__name__)


class PlaceQueryParams(TypedDict):
    lat: float
    lng: float
    search_radius: int
    category: NotRequired[str]
    category_group: NotRequired[str]


OpenStreetMapPayload = dict[str, Any]


class OpenStreetMapResourceUnavailable(APIException):
    """
    Raised when the OpenStreetMap service is unavailable or returns bad data.
    """

    status_code = 503
    default_detail = "OpenStreetMap resource is not available."
    default_code = "service_unavailable"


def request_places(query_params: PlaceQueryParams) -> httpx.Response:
    """
    Connection with the OpenStreetMap Overpass API.
    """

    max_attempts = settings.OPEN_STREET_MAP_MAX_RETRIES + 1
    request_payload = build_request_payload(query_params)
    overpass_urls = get_overpass_urls()

    for attempt in range(1, max_attempts + 1):
        last_error: httpx.RequestError | None = None
        for overpass_url in overpass_urls:
            try:
                response = httpx.get(
                    overpass_url,
                    headers=headers(),
                    params=request_payload,
                    timeout=settings.OPEN_STREET_MAP_TIMEOUT_IN_SECS,
                )
            except httpx.RequestError as exc:
                last_error = exc
                logger.warning(
                    "OpenStreetMap request to %s failed on attempt %s/%s: %s",
                    overpass_url,
                    attempt,
                    max_attempts,
                    exc,
                )
                continue

            if should_retry_response(response) and attempt < max_attempts:
                logger.warning(
                    "OpenStreetMap endpoint %s returned retryable status %s on attempt %s/%s",
                    overpass_url,
                    response.status_code,
                    attempt,
                    max_attempts,
                )
                continue

            return response

        if attempt < max_attempts:
            wait_before_retry(attempt)
            continue

        logger.warning(
            "OpenStreetMap request failed on final attempt %s/%s",
            attempt,
            max_attempts,
        )
        if last_error is not None:
            raise OpenStreetMapResourceUnavailable() from last_error

    raise OpenStreetMapResourceUnavailable()


def fetch_places_payload(
    query_params: PlaceQueryParams,
) -> OpenStreetMapPayload:
    cached_payload = cache.get_payload(query_params)

    if cached_payload is not None:
        return cached_payload

    response = request_places(query_params)

    if response.status_code != httpx.codes.OK:
        logger.warning(
            "OpenStreetMap returned status %s: %s",
            response.status_code,
            response.text[:500],
        )
        raise OpenStreetMapResourceUnavailable()

    try:
        payload = response.json()
    except ValueError as exc:
        logger.warning("OpenStreetMap returned invalid JSON: %s", exc)
        raise OpenStreetMapResourceUnavailable() from exc

    if not isinstance(payload, dict):
        logger.warning(
            "OpenStreetMap returned unexpected payload type: %s", type(payload)
        )
        raise OpenStreetMapResourceUnavailable()

    cache.set_payload(query_params, payload)

    return payload


def build_request_payload(query_params: PlaceQueryParams) -> dict[str, str]:
    return {
        "data": build_overpass_query(
            lat=query_params["lat"],
            lng=query_params["lng"],
            radius=query_params["search_radius"],
            category=query_params.get("category"),
            category_group=query_params.get("category_group"),
        )
    }


def build_overpass_query(
    lat: float,
    lng: float,
    radius: int,
    category: str | None = None,
    category_group: str | None = None,
) -> str:
    if category is not None:
        osm_tags = get_osm_category_tags_for_slug(category)
    elif category_group:
        osm_tags = get_osm_category_tags_for_group(category_group)
    else:
        osm_tags = get_default_osm_category_tags()

    if not osm_tags:
        raise OpenStreetMapResourceUnavailable()

    filters = "\n".join(
        f'  nwr(around:{radius},{lat},{lng})["{key}"="{value}"];'
        for key, value in osm_tags
    )

    return f"""
            [out:json][timeout:25];
            (
            {filters}
            );
            out center tags qt 50;
            """


def headers() -> dict[str, str]:
    return {
        "Accept": "application/json",
        "User-Agent": settings.OPEN_STREET_MAP_USER_AGENT,
    }


def get_overpass_urls() -> list[str]:
    urls = list(settings.OPEN_STREET_MAP_OVERPASS_URLS)

    return urls or [settings.OPEN_STREET_MAP_OVERPASS_URL]


def should_retry_response(response: httpx.Response) -> bool:
    return response.status_code in RETRYABLE_STATUS_CODES


def wait_before_retry(attempt: int) -> None:
    time.sleep(min(0.5 * attempt, 2.0))
