from rest_framework import serializers

from geo.models import Country, ServiceArea


class CountrySerializer(serializers.ModelSerializer[Country]):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = Country
        fields = (
            "id",
            "code",
            "name",
            "default_language",
            "timezone",
            "currency",
        )


class ServiceAreaSerializer(serializers.ModelSerializer[ServiceArea]):
    country = CountrySerializer(read_only=True)
    center = serializers.SerializerMethodField()

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = ServiceArea
        fields = (
            "id",
            "slug",
            "name",
            "area_type",
            "country",
            "center",
            "population",
            "timezone",
        )

    def get_center(self, service_area: ServiceArea) -> dict[str, float]:
        return {
            "lat": service_area.latitude,
            "lng": service_area.longitude,
        }
