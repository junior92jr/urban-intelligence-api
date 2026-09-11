from typing import Any, ClassVar, override

from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.db import models
from django.db.models import Q

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


class OsmImportRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        SUPERSEDED = "superseded", "Superseded"

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    source_object_key = models.CharField(max_length=512)
    city_slug = models.SlugField()
    source_sha256 = models.CharField(max_length=64, blank=True)
    source_timestamp = models.DateTimeField(null=True, blank=True)
    current_stage = models.CharField(max_length=120, blank=True)
    total_cities = models.PositiveIntegerField(default=0)
    processed_cities = models.PositiveIntegerField(default=0)
    error_summary = models.TextField(blank=True)
    is_active = models.BooleanField(default=False)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["city_slug"],
                condition=Q(is_active=True, city_slug__gt=""),
                name="unique_active_osm_import_per_city",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["status", "is_active"],
                name="osm_import_status_idx",
            ),
            models.Index(
                fields=["city_slug", "is_active"],
                name="osm_import_city_idx",
            ),
        ]

    @override
    def __str__(self) -> str:
        return f"OSM import {self.pk} ({self.status})"


class ServiceAreaQuerySet(models.QuerySet["ServiceArea"]):
    def active(self) -> "ServiceAreaQuerySet":
        """Return the active OSM dataset, or legacy manual areas before one exists."""
        active_city_slugs = OsmImportRun.objects.filter(
            is_active=True,
        ).values("city_slug")
        return self.filter(
            Q(import_run__is_active=True)
            | (Q(import_run__isnull=True) & ~Q(slug__in=active_city_slugs)),
            is_active=True,
        )

    def cities(self) -> "ServiceAreaQuerySet":
        return self.filter(area_type=ServiceArea.AreaType.CITY)

    def districts(self) -> "ServiceAreaQuerySet":
        return self.filter(area_type=ServiceArea.AreaType.DISTRICT)

    def neighborhoods(self) -> "ServiceAreaQuerySet":
        return self.filter(area_type=ServiceArea.AreaType.NEIGHBORHOOD)


class ServiceAreaManager(models.Manager["ServiceArea"]):
    @override
    def get_queryset(self) -> ServiceAreaQuerySet:
        return ServiceAreaQuerySet(self.model, using=self._db)

    def active(self) -> ServiceAreaQuerySet:
        return self.get_queryset().active()

    def cities(self) -> ServiceAreaQuerySet:
        return self.get_queryset().cities()

    def districts(self) -> ServiceAreaQuerySet:
        return self.get_queryset().districts()

    def neighborhoods(self) -> ServiceAreaQuerySet:
        return self.get_queryset().neighborhoods()


class ServiceArea(models.Model):
    class AreaType(models.TextChoices):
        REGION = "region", "Region"
        CITY = "city", "City"
        DISTRICT = "district", "District"
        NEIGHBORHOOD = "neighborhood", "Neighborhood"

    class SourceType(models.TextChoices):
        MANUAL = "manual", "Manual"
        OSM = "osm", "OpenStreetMap"

    class OsmElementType(models.TextChoices):
        NODE = "node", "Node"
        WAY = "way", "Way"
        RELATION = "relation", "Relation"

    import_run = models.ForeignKey(
        OsmImportRun,
        on_delete=models.CASCADE,
        related_name="service_areas",
        null=True,
        blank=True,
    )

    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="service_areas",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True,
    )
    slug = models.SlugField(max_length=250)
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
    source = models.CharField(
        max_length=32,
        choices=SourceType.choices,
        default=SourceType.MANUAL,
    )
    source_id = models.CharField(max_length=120, blank=True)
    osm_element_type = models.CharField(
        max_length=16,
        choices=OsmElementType.choices,
        blank=True,
    )
    osm_admin_level = models.PositiveSmallIntegerField(null=True, blank=True)
    osm_tags = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    objects: ClassVar[ServiceAreaManager] = ServiceAreaManager()  # pyright: ignore[reportIncompatibleVariableOverride]

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["country", "slug"],
                name="unique_service_area_slug_per_country",
            ),
            models.UniqueConstraint(
                fields=["import_run", "source", "osm_element_type", "source_id"],
                condition=Q(
                    source="osm",
                    source_id__gt="",
                    osm_element_type__gt="",
                ),
                name="unique_osm_area_per_import",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["country", "area_type", "is_active"],
                name="service_area_lookup_idx",
            ),
            models.Index(
                fields=["parent", "area_type"],
                name="service_area_parent_idx",
            ),
            models.Index(
                fields=["import_run", "area_type"],
                name="service_area_import_idx",
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
