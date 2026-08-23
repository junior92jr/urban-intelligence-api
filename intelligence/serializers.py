from typing import Any

from rest_framework import serializers

from intelligence.models import (
    AreaIndicatorObservation,
    IntelligenceIndicator,
    IntelligenceSource,
)


class IntelligenceSourceSerializer(serializers.ModelSerializer[IntelligenceSource]):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = IntelligenceSource
        fields = ("name", "attribution")


class AreaIndicatorObservationSerializer(
    serializers.ModelSerializer[AreaIndicatorObservation]
):
    source = IntelligenceSourceSerializer(  # type: ignore[assignment]  # pyright: ignore[reportAssignmentType]
        read_only=True,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = AreaIndicatorObservation
        fields = (
            "score",
            "trend",
            "source",
            "methodology",
            "observed_at",
            "expires_at",
        )


class AreaIntelligenceIndicatorSerializer(serializers.Serializer[dict[str, Any]]):
    slug = serializers.SlugField()
    name = serializers.CharField()
    value_type = serializers.ChoiceField(
        choices=IntelligenceIndicator.ValueType.choices
    )
    observation = AreaIndicatorObservationSerializer(allow_null=True)
