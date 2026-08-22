from typing import Any, cast

from django.contrib.auth.models import AbstractBaseUser
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.models import UserProfile
from intelligence.models import IntelligenceIndicator
from intelligence.serializers import AreaIntelligenceIndicatorSerializer
from intelligence.services.observations import get_area_intelligence


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
