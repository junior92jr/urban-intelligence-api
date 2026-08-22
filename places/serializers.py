from typing import Any, cast, override

from rest_framework import serializers

from .models import AreaScan, DiscoveredPlace, PlaceCategory
from .services.categories import get_category_by_slug
from .services.open_street_map import PlaceQueryParams

DEFAULT_SEARCH_RADIUS = 500
MAX_SEARCH_RADIUS = 3000


class CategorySerializer(serializers.ModelSerializer[PlaceCategory]):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = PlaceCategory
        fields = ("slug", "name", "group")


class DiscoveredPlaceSerializer(serializers.ModelSerializer[DiscoveredPlace]):
    latitude = serializers.FloatField(read_only=True)
    longitude = serializers.FloatField(read_only=True)
    distance_meters = serializers.SerializerMethodField()

    def get_distance_meters(self, place: DiscoveredPlace) -> int | None:
        distance = getattr(place, "distance", None)

        return round(distance.m) if distance is not None else None

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = DiscoveredPlace
        fields = (
            "osm_id",
            "osm_type",
            "name",
            "latitude",
            "longitude",
            "distance_meters",
            "category",
            "category_name",
            "category_group",
            "osm_uid",
            "address",
            "website",
            "opening_hours",
        )


class AreaScanSerializer(serializers.ModelSerializer[AreaScan]):
    latitude = serializers.FloatField(read_only=True)
    longitude = serializers.FloatField(read_only=True)

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = AreaScan
        fields = (
            "id",
            "latitude",
            "longitude",
            "radius",
            "category",
            "category_group",
            "status",
            "result_count",
            "error_message",
            "created_at",
            "started_at",
            "completed_at",
        )


class RecommendationsQuerySerializer(serializers.Serializer[dict[str, Any]]):
    """
    Serializer that handles validation for the request parameters.
    """

    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)
    search_radius = serializers.IntegerField(
        min_value=1,
        max_value=MAX_SEARCH_RADIUS,
        required=False,
    )
    search_radious = serializers.IntegerField(
        min_value=1,
        max_value=MAX_SEARCH_RADIUS,
        required=False,
    )
    category = serializers.CharField(required=False)
    category_group = serializers.ChoiceField(
        choices=PlaceCategory.Group.choices,
        required=False,
    )

    @override
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        search_radius = attrs.get("search_radius")
        legacy_search_radius = attrs.get("search_radious")

        if (
            search_radius is not None
            and legacy_search_radius is not None
            and search_radius != legacy_search_radius
        ):
            raise serializers.ValidationError(
                {"search_radius": "Use only one search radius value."}
            )

        if (
            attrs.get("category") is not None
            and attrs.get("category_group") is not None
        ):
            raise serializers.ValidationError(
                {"category_group": "Use either category or category group."}
            )

        return attrs

    def validate_category(self, value: str) -> str:
        if get_category_by_slug(value) is None:
            raise serializers.ValidationError("Unknown category.")

        return value

    def to_query_params(self) -> PlaceQueryParams:
        validated_data = cast(dict[str, Any], self.validated_data)
        search_radius = validated_data.get(
            "search_radius",
            validated_data.get("search_radious", DEFAULT_SEARCH_RADIUS),
        )
        query_params: PlaceQueryParams = {
            "lat": cast(float, validated_data["lat"]),
            "lng": cast(float, validated_data["lng"]),
            "search_radius": cast(int, search_radius),
        }

        category = validated_data.get("category")
        category_group = validated_data.get("category_group")

        if category is not None:
            query_params["category"] = cast(str, category)
        if category_group is not None:
            query_params["category_group"] = cast(str, category_group)

        return query_params


class NearbyPlacesQuerySerializer(RecommendationsQuerySerializer):
    pass


class AreaScanCreateSerializer(RecommendationsQuerySerializer):
    pass
