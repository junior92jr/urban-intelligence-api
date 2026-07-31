from typing import Any, cast, override

from rest_framework import serializers

from user_places.models import FavoritePlace, SearchHistory, build_point


class FavoritePlaceSerializer(serializers.ModelSerializer[FavoritePlace]):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = FavoritePlace
        fields = (
            "id",
            "osm_uid",
            "osm_id",
            "osm_type",
            "name",
            "category",
            "category_name",
            "latitude",
            "longitude",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    @override
    def create(self, validated_data: dict[str, Any]) -> FavoritePlace:
        user = self.context["request"].user
        latitude = cast(float, validated_data.pop("latitude"))
        longitude = cast(float, validated_data.pop("longitude"))
        validated_data["location"] = build_point(
            latitude=latitude,
            longitude=longitude,
        )
        favorite, _ = FavoritePlace.objects.get_or_create(
            user=user,
            osm_uid=cast(str, validated_data["osm_uid"]),
            defaults=validated_data,
        )

        return favorite


class SearchHistorySerializer(serializers.ModelSerializer[SearchHistory]):
    latitude = serializers.FloatField(read_only=True)
    longitude = serializers.FloatField(read_only=True)

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = SearchHistory
        fields = (
            "id",
            "latitude",
            "longitude",
            "search_radius",
            "category",
            "result_count",
            "created_at",
        )
        read_only_fields = fields
