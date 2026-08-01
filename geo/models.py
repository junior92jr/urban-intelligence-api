from typing import Any, ClassVar, override

from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.db import models

POINT_SRID = 4326


def build_point(*, latitude: float, longitude: float) -> Point:
    return Point(longitude, latitude, srid=POINT_SRID)


class Country(models.Model):
    code = models.CharField(max_length=2, unique=True)
    name = models.CharField(max_length=120)
    default_language = models.CharField(max_length=16, blank=True)
    timezone = models.CharField(max_length=64, blank=True)
    currency = models.CharField(max_length=3, blank=True)
    data_config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name_plural = "countries"

    @override
    def __str__(self) -> str:
        return self.name

    @override
    def save(self, *args: Any, **kwargs: Any) -> None:
        self.code = self.code.upper()
        super().save(*args, **kwargs)


class ServiceArea(models.Model):
    class AreaType(models.TextChoices):
        CITY = "city", "City"
        DISTRICT = "district", "District"
        REGION = "region", "Region"

    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="service_areas",
    )
    slug = models.SlugField()
    name = models.CharField(max_length=160)
    area_type = models.CharField(
        max_length=32,
        choices=AreaType.choices,
        default=AreaType.CITY,
    )
    center = gis_models.PointField(srid=POINT_SRID)
    boundary = gis_models.MultiPolygonField(srid=POINT_SRID, null=True, blank=True)
    bbox = gis_models.PolygonField(srid=POINT_SRID, null=True, blank=True)
    population = models.PositiveIntegerField(null=True, blank=True)
    timezone = models.CharField(max_length=64, blank=True)
    data_config = models.JSONField(default=dict, blank=True)
    source = models.CharField(max_length=120, blank=True)
    source_id = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["country", "slug"],
                name="unique_service_area_slug_per_country",
            ),
        ]
        ordering = ("country__sort_order", "sort_order", "name")

    @override
    def __str__(self) -> str:
        return f"{self.name}, {self.country.code}"

    @property
    def latitude(self) -> float:
        return float(self.center.y)

    @property
    def longitude(self) -> float:
        return float(self.center.x)
