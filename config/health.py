from http import HTTPStatus
from typing import Any

from django.core.cache import cache
from django.db import DatabaseError, connections
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from redis.exceptions import RedisError


@require_GET
def live(_request: Any) -> JsonResponse:
    return JsonResponse({"status": "ok"})


@require_GET
def ready(_request: Any) -> JsonResponse:
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        cache.set("healthcheck", "ok", timeout=10)
        if cache.get("healthcheck") != "ok":
            raise RuntimeError("Cache health check failed")
    except (DatabaseError, RedisError, RuntimeError) as exc:
        return JsonResponse(
            {"status": "unavailable", "error": str(exc)},
            status=HTTPStatus.SERVICE_UNAVAILABLE,
        )

    return JsonResponse({"status": "ok"})
