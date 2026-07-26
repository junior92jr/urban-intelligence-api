from typing import ClassVar, override

from django.conf import settings
from django.db import models


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
    latitude = models.FloatField()
    longitude = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["user", "osm_uid"],
                name="unique_favorite_place_per_user",
            ),
        ]
        ordering = ("-created_at",)

    @override
    def __str__(self) -> str:
        return f"{self.user} - {self.name}"


class SearchHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="place_searches",
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    search_radius = models.PositiveIntegerField()
    category = models.CharField(max_length=100, blank=True)
    result_count = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    @override
    def __str__(self) -> str:
        return f"{self.user} - {self.latitude}, {self.longitude}"
