from django.conf import settings
from django.core.checks import CheckMessage, Error, Tags, Warning, register


@register(Tags.security, deploy=True)
def production_environment_check(
    app_configs: object,
    **kwargs: object,
) -> list[CheckMessage]:
    if settings.DEBUG:
        return []

    issues: list[CheckMessage] = []

    if settings.SECRET_KEY.startswith("django-insecure"):
        issues.append(
            Error(
                "Production SECRET_KEY must not use a development value.",
                id="city_guide.E001",
            ),
        )

    if not settings.ALLOWED_HOSTS:
        issues.append(
            Error(
                "Production ALLOWED_HOSTS must include at least one host.",
                id="city_guide.E002",
            ),
        )

    if "tile.openstreetmap.org" in settings.MAP_TILE_URL:
        issues.append(
            Warning(
                "Production MAP_TILE_URL should use a dedicated tile provider.",
                hint="Configure MAP_TILE_URL and MAP_TILE_ATTRIBUTION for production traffic.",
                id="city_guide.W001",
            ),
        )

    if settings.EMAIL_BACKEND.endswith(".console.EmailBackend"):
        issues.append(
            Warning(
                "Production email is using the console backend.",
                hint="Configure SMTP settings before sending real account emails.",
                id="city_guide.W002",
            ),
        )

    if not settings.REDIS_URL:
        issues.append(
            Warning(
                "Production cache is not using Redis.",
                hint="Set REDIS_URL to keep cache behavior consistent across containers.",
                id="city_guide.W003",
            ),
        )

    return issues
