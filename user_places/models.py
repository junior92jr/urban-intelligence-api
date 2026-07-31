from typing import ClassVar, override

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.contrib.postgres.indexes import GistIndex
from django.db import models

POINT_SRID = 4326


def build_point(*, latitude: float, longitude: float) -> Point:
    return Point(longitude, latitude, srid=POINT_SRID)


class FavoritePlace(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_places",
    )
    osm_uid = models.CharField(max_length=128)
    osm_id = models.BigIntegerField()
    osm_type = models.CharField(max_length=32)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    category_name = models.CharField(max_length=255)
    location = gis_models.PointField(srid=POINT_SRID)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["user", "osm_uid"],
                name="unique_favorite_place_per_user",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            GistIndex(fields=["location"], name="favorite_place_location_gist"),
        ]
        ordering = ("-created_at",)

    @override
    def __str__(self) -> str:
        return f"{self.user} - {self.name}"

    @property
    def latitude(self) -> float:
        return float(self.location.y)

    @property
    def longitude(self) -> float:
        return float(self.location.x)


class SearchHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="place_searches",
    )
    location = gis_models.PointField(srid=POINT_SRID)
    search_radius = models.PositiveIntegerField()
    category = models.CharField(max_length=100, blank=True)
    result_count = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes: ClassVar[list[models.Index]] = [
            GistIndex(fields=["location"], name="search_history_location_gist"),
        ]
        ordering = ("-created_at",)

    @override
    def __str__(self) -> str:
        return f"{self.user} - {self.latitude}, {self.longitude}"

    @property
    def latitude(self) -> float:
        return float(self.location.y)

    @property
    def longitude(self) -> float:
        return float(self.location.x)
