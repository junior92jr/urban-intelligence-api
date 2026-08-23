from typing import ClassVar, override

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


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


class IntelligenceDataset(models.Model):
    source = models.ForeignKey(
        IntelligenceSource,
        on_delete=models.PROTECT,
        related_name="datasets",
    )
    indicator = models.ForeignKey(
        IntelligenceIndicator,
        on_delete=models.PROTECT,
        related_name="datasets",
    )
    slug = models.SlugField()
    name = models.CharField(max_length=160)
    reference_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("source__sort_order", "sort_order", "name")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=("source", "slug"),
                name="unique_intelligence_dataset_per_source",
            ),
        ]

    @override
    def __str__(self) -> str:
        return f"{self.source}: {self.name}"


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


class IntelligenceImport(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    dataset = models.ForeignKey(
        IntelligenceDataset,
        on_delete=models.PROTECT,
        related_name="imports",
    )
    service_area = models.ForeignKey(
        "geo.ServiceArea",
        on_delete=models.CASCADE,
        related_name="intelligence_imports",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="requested_intelligence_imports",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
    )
    dataset_version = models.CharField(max_length=100, blank=True)
    reference_date = models.DateField(null=True, blank=True)
    result_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["dataset", "service_area", "status"],
                name="intel_import_dataset_area_idx",
            ),
            models.Index(
                fields=["created_at"],
                name="intel_import_created_idx",
            ),
        ]

    @override
    def __str__(self) -> str:
        return f"{self.dataset} import for {self.service_area}"
