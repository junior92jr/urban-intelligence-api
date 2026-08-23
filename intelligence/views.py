import json
from typing import Any, cast

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser
from django.http import Http404, StreamingHttpResponse
from django.urls import reverse
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.models import UserProfile
from geo.models import ServiceArea
from intelligence.models import AreaIndicatorObservation, IntelligenceIndicator
from intelligence.serializers import AreaIntelligenceIndicatorSerializer
from intelligence.services.observations import get_area_intelligence
from intelligence.services.providers.copernicus import get_cache_storage_client


class AreaIntelligenceView(GenericAPIView[Any]):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        user = request.user
        assert isinstance(user, AbstractBaseUser)
        profile = UserProfile.get_for_user(user)

        if profile.service_area is None:
            raise ValidationError(
                {
                    "service_area": "Complete onboarding before viewing area intelligence."
                }
            )

        groups: dict[str, list[dict[str, Any]]] = {}
        for indicator, observation in get_area_intelligence(
            service_area=profile.service_area,
        ):
            if observation is None:
                continue

            groups.setdefault(indicator.group, []).append(
                {
                    "slug": indicator.slug,
                    "name": indicator.name,
                    "value_type": indicator.value_type,
                    "observation": observation,
                }
            )

        return Response(
            {
                "service_area": {
                    "slug": profile.service_area.slug,
                    "name": profile.service_area.name,
                },
                "groups": [
                    {
                        "slug": group,
                        "name": label,
                        "indicators": AreaIntelligenceIndicatorSerializer(
                            cast(Any, groups[group]),
                            many=True,
                        ).data,
                    }
                    for group, label in IntelligenceIndicator.Group.choices
                    if group in groups
                ],
            }
        )


class TreeCoverDensityMapLayerView(GenericAPIView[Any]):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        profile = get_user_profile(request)
        observation = get_tree_cover_observation(profile.service_area)
        map_layer = observation.details.get("map_layer", {})
        layers = map_layer.get("layers", [])
        if not layers:
            raise Http404

        service_area = observation.service_area
        assert service_area.boundary is not None
        return Response(
            {
                "title": str(map_layer.get("title", "Tree cover")),
                "summary": (
                    f"Around {observation.score}% average tree canopy cover across "
                    f"{service_area.name}."
                ),
                "source": observation.source.name,
                "reference_date": observation.observed_at.date().isoformat(),
                "boundary": json.loads(service_area.boundary.geojson),
                "layers": [
                    {
                        "bounds": layer["bounds"],
                        "image_url": request.build_absolute_uri(
                            reverse(
                                "places:tree-cover-density-layer-image",
                                kwargs={"layer_index": index},
                            )
                        ),
                    }
                    for index, layer in enumerate(layers)
                ],
            }
        )


class TreeCoverDensityLayerImageView(GenericAPIView[Any]):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request, layer_index: int) -> StreamingHttpResponse:
        profile = get_user_profile(request)
        observation = get_tree_cover_observation(profile.service_area)
        map_layer = observation.details.get("map_layer", {})
        layers = map_layer.get("layers", [])

        try:
            object_key = str(layers[layer_index]["object_key"])
        except (IndexError, KeyError, TypeError) as exc:
            raise Http404 from exc

        try:
            response = get_cache_storage_client().get_object(
                Bucket=settings.OBJECT_STORAGE_BUCKET,
                Key=object_key,
            )
        except Exception as exc:
            raise Http404 from exc

        body = response["Body"]
        return StreamingHttpResponse(
            stream_object_body(body),
            content_type="image/png",
        )


def get_user_profile(request: Request) -> UserProfile:
    user = request.user
    assert isinstance(user, AbstractBaseUser)
    profile = UserProfile.get_for_user(user)
    if profile.service_area is None:
        raise ValidationError(
            {"service_area": "Complete onboarding before viewing area intelligence."}
        )
    return profile


def get_tree_cover_observation(
    service_area: ServiceArea | None,
) -> AreaIndicatorObservation:
    observation = (
        AreaIndicatorObservation.objects.select_related("service_area", "source")
        .filter(
            service_area=service_area,
            indicator__slug="green-exposure",
            source__slug="copernicus-land-monitoring",
        )
        .order_by("-observed_at")
        .first()
    )
    if observation is None:
        raise Http404
    return observation


def stream_object_body(body: Any) -> Any:
    try:
        while chunk := body.read(1024 * 1024):
            yield chunk
    finally:
        body.close()
