from typing import ClassVar, override

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.indexes import GistIndex
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class PlaceCategory(models.Model):
    class Group(models.TextChoices):
        ESSENTIALS = "essentials", "Essentials"
        FOOD = "food", "Food"
        TOURISM = "tourism", "Tourism"
        MOBILITY = "mobility", "Mobility"

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    group = models.CharField(
        max_length=32,
        choices=Group.choices,
        default=Group.ESSENTIALS,
    )
    osm_key = models.CharField(max_length=50)
    osm_value = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    include_in_default_search = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=("osm_key", "osm_value"),
                name="unique_place_category_osm_tag",
            ),
        ]
        verbose_name = "place category"
        verbose_name_plural = "place categories"

    @override
    def __str__(self) -> str:
        return str(self.name)


class DiscoveredPlace(models.Model):
    class Source(models.TextChoices):
        OPEN_STREET_MAP = "open_street_map", "OpenStreetMap"

    service_area = models.ForeignKey(
        "geo.ServiceArea",
        on_delete=models.CASCADE,
        related_name="discovered_places",
    )
    osm_uid = models.CharField(max_length=128)
    osm_id = models.BigIntegerField()
    osm_type = models.CharField(max_length=32)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    category_name = models.CharField(max_length=255)
    category_group = models.CharField(max_length=32)
    location = gis_models.PointField(srid=4326)
    address = models.CharField(max_length=500, blank=True)
    website = models.URLField(blank=True)
    opening_hours = models.CharField(max_length=255, blank=True)
    tags = models.JSONField(default=dict, blank=True)
    source = models.CharField(
        max_length=32,
        choices=Source.choices,
        default=Source.OPEN_STREET_MAP,
    )
    fetched_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        indexes: ClassVar[list[models.Index]] = [
            GistIndex(fields=["location"], name="discovered_place_location_gist"),
            models.Index(
                fields=["service_area", "category"],
                name="disc_place_area_cat_idx",
            ),
            models.Index(
                fields=["service_area", "category_group"],
                name="disc_place_area_group_idx",
            ),
        ]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=("service_area", "osm_uid"),
                name="unique_discovered_place_per_service_area",
            ),
        ]

    @override
    def __str__(self) -> str:
        return self.name

    @property
    def latitude(self) -> float:
        return float(self.location.y)

    @property
    def longitude(self) -> float:
        return float(self.location.x)


class AreaScan(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="area_scans",
        null=True,
        blank=True,
    )
    service_area = models.ForeignKey(
        "geo.ServiceArea",
        on_delete=models.CASCADE,
        related_name="area_scans",
    )
    center = gis_models.PointField(srid=4326)
    radius = models.PositiveIntegerField()
    category = models.CharField(max_length=100, blank=True)
    category_group = models.CharField(
        max_length=32,
        choices=PlaceCategory.Group.choices,
        blank=True,
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
    )
    result_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes: ClassVar[list[models.Index]] = [
            GistIndex(fields=["center"], name="area_scan_center_gist"),
            models.Index(
                fields=["service_area", "status"],
                name="area_scan_area_status_idx",
            ),
            models.Index(fields=["created_at"], name="area_scan_created_at_idx"),
        ]

    @override
    def __str__(self) -> str:
        return f"{self.service_area} scan {self.status}"

    @property
    def latitude(self) -> float:
        return float(self.center.y)

    @property
    def longitude(self) -> float:
        return float(self.center.x)


class DataImport(models.Model):
    class Source(models.TextChoices):
        OPEN_STREET_MAP = "open_street_map", "OpenStreetMap"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    source = models.CharField(
        max_length=32,
        choices=Source.choices,
        default=Source.OPEN_STREET_MAP,
    )
    service_area = models.ForeignKey(
        "geo.ServiceArea",
        on_delete=models.CASCADE,
        related_name="data_imports",
    )
    category_group = models.CharField(
        max_length=32,
        choices=PlaceCategory.Group.choices,
    )
    radius = models.PositiveIntegerField(default=8000)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="requested_data_imports",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
    )
    result_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["source", "service_area", "status"],
                name="data_import_source_area_idx",
            ),
            models.Index(fields=["created_at"], name="data_import_created_idx"),
        ]

    @override
    def __str__(self) -> str:
        return f"{self.source} import for {self.service_area}"


class IntelligenceSource(models.Model):
    """A provider from which area intelligence can be derived."""

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=160)
    attribution = models.CharField(max_length=255, blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name = "intelligence source"
        verbose_name_plural = "intelligence sources"

    @override
    def __str__(self) -> str:
        return self.name


class IntelligenceIndicator(models.Model):
    class Group(models.TextChoices):
        MOBILITY = "mobility", "Mobility"
        URBAN_ENVIRONMENT = "urban_environment", "Urban environment"
        DAILY_LIFE = "daily_life", "Daily life"
        DYNAMICS = "dynamics", "Dynamics"

    class ValueType(models.TextChoices):
        SCORE = "score", "Score"
        TREND = "trend", "Trend"

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=160)
    group = models.CharField(max_length=32, choices=Group.choices)
    value_type = models.CharField(max_length=16, choices=ValueType.choices)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("group", "sort_order", "name")
        verbose_name = "intelligence indicator"
        verbose_name_plural = "intelligence indicators"

    @override
    def __str__(self) -> str:
        return self.name


class AreaIndicatorObservation(models.Model):
    class Trend(models.TextChoices):
        UP = "up", "Increasing"
        STEADY = "steady", "Steady"
        DOWN = "down", "Decreasing"

    service_area = models.ForeignKey(
        "geo.ServiceArea",
        on_delete=models.CASCADE,
        related_name="indicator_observations",
    )
    indicator = models.ForeignKey(
        IntelligenceIndicator,
        on_delete=models.CASCADE,
        related_name="observations",
    )
    source = models.ForeignKey(
        IntelligenceSource,
        on_delete=models.PROTECT,
        related_name="observations",
    )
    score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    trend = models.CharField(max_length=16, choices=Trend.choices, blank=True)
    methodology = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)
    observed_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-observed_at",)
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["service_area", "indicator", "-observed_at"],
                name="area_indicator_observation_idx",
            ),
            models.Index(
                fields=["source", "-observed_at"],
                name="indicator_source_observed_idx",
            ),
        ]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(score__isnull=False) | ~models.Q(trend=""),
                name="area_indicator_has_value",
            ),
        ]

    @override
    def __str__(self) -> str:
        return f"{self.indicator} for {self.service_area}"
