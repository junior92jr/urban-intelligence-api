from typing import Any, cast, override

from rest_framework import serializers

from user_places.models import FavoritePlace


class FavoritePlaceSerializer(serializers.ModelSerializer[FavoritePlace]):
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
        favorite, _ = FavoritePlace.objects.get_or_create(
            user=user,
            osm_uid=cast(str, validated_data["osm_uid"]),
            defaults=validated_data,
        )

        return favorite
