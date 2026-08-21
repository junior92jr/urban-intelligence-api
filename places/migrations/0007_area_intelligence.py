import django.core.validators
import django.db.models.deletion
from django.db import migrations, models

INDICATORS = (
    ("transit-accessibility", "Transit accessibility", "mobility", "score"),
    ("cycling-accessibility", "Cycling accessibility", "mobility", "score"),
    ("walkability", "Walkability", "mobility", "score"),
    ("car-dependency", "Car dependency", "mobility", "score"),
    ("green-exposure", "Green exposure", "urban_environment", "score"),
    ("traffic-exposure", "Traffic exposure", "urban_environment", "score"),
    ("building-density", "Building density", "urban_environment", "score"),
    ("essentials-accessibility", "Essentials accessibility", "daily_life", "score"),
    ("schools-accessibility", "Schools accessibility", "daily_life", "score"),
    ("healthcare-accessibility", "Healthcare accessibility", "daily_life", "score"),
    ("construction-activity", "Construction activity", "dynamics", "trend"),
    ("traffic", "Traffic", "dynamics", "trend"),
    ("development-intensity", "Development intensity", "dynamics", "trend"),
)

SOURCES = (
    (
        "open-street-map",
        "OpenStreetMap",
        "OpenStreetMap contributors",
        "https://www.openstreetmap.org",
    ),
    (
        "frankfurt-open-data",
        "Frankfurt Open Data",
        "City of Frankfurt",
        "https://offenedaten.frankfurt.de",
    ),
    ("frankfurt-gis", "Frankfurt GIS", "City of Frankfurt", ""),
    ("rmv", "RMV", "Rhein-Main-Verkehrsverbund", "https://www.rmv.de"),
    (
        "destatis",
        "Destatis",
        "Federal Statistical Office of Germany",
        "https://www.destatis.de",
    ),
    (
        "umweltbundesamt",
        "Umweltbundesamt",
        "German Environment Agency",
        "https://www.umweltbundesamt.de",
    ),
    ("hessen-police", "Hessen Police", "Hesse Police", "https://innen.hessen.de"),
)


def seed_intelligence_catalog(apps, schema_editor):
    indicator = apps.get_model("places", "IntelligenceIndicator")
    source = apps.get_model("places", "IntelligenceSource")

    for sort_order, (slug, name, group, value_type) in enumerate(INDICATORS):
        indicator.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "group": group,
                "value_type": value_type,
                "is_active": True,
                "sort_order": sort_order,
            },
        )

    for sort_order, (slug, name, attribution, website) in enumerate(SOURCES):
        source.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "attribution": attribution,
                "website": website,
                "is_active": True,
                "sort_order": sort_order,
            },
        )


def remove_intelligence_catalog(apps, schema_editor):
    apps.get_model("places", "IntelligenceIndicator").objects.filter(
        slug__in=[slug for slug, *_rest in INDICATORS]
    ).delete()
    apps.get_model("places", "IntelligenceSource").objects.filter(
        slug__in=[slug for slug, *_rest in SOURCES]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [  # noqa: RUF012
        ("geo", "0001_initial"),
        ("places", "0006_dataimport"),
    ]

    operations = [  # noqa: RUF012
        migrations.CreateModel(
            name="IntelligenceIndicator",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=160)),
                (
                    "group",
                    models.CharField(
                        choices=[
                            ("mobility", "Mobility"),
                            ("urban_environment", "Urban environment"),
                            ("daily_life", "Daily life"),
                            ("dynamics", "Dynamics"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "value_type",
                    models.CharField(
                        choices=[("score", "Score"), ("trend", "Trend")],
                        max_length=16,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "intelligence indicator",
                "verbose_name_plural": "intelligence indicators",
                "ordering": ("group", "sort_order", "name"),
            },
        ),
        migrations.CreateModel(
            name="IntelligenceSource",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=160)),
                ("attribution", models.CharField(blank=True, max_length=255)),
                ("website", models.URLField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "intelligence source",
                "verbose_name_plural": "intelligence sources",
                "ordering": ("sort_order", "name"),
            },
        ),
        migrations.CreateModel(
            name="AreaIndicatorObservation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "score",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(100),
                        ],
                    ),
                ),
                (
                    "trend",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("up", "Increasing"),
                            ("steady", "Steady"),
                            ("down", "Decreasing"),
                        ],
                        max_length=16,
                    ),
                ),
                ("methodology", models.CharField(blank=True, max_length=255)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("observed_at", models.DateTimeField()),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "indicator",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="observations",
                        to="places.intelligenceindicator",
                    ),
                ),
                (
                    "service_area",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="indicator_observations",
                        to="geo.servicearea",
                    ),
                ),
                (
                    "source",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="observations",
                        to="places.intelligencesource",
                    ),
                ),
            ],
            options={"ordering": ("-observed_at",)},
        ),
        migrations.AddIndex(
            model_name="areaindicatorobservation",
            index=models.Index(
                fields=["service_area", "indicator", "-observed_at"],
                name="area_indicator_observation_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="areaindicatorobservation",
            index=models.Index(
                fields=["source", "-observed_at"],
                name="indicator_source_observed_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="areaindicatorobservation",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("score__isnull", False),
                    models.Q(("trend", ""), _negated=True),
                    _connector="OR",
                ),
                name="area_indicator_has_value",
            ),
        ),
        migrations.RunPython(
            seed_intelligence_catalog,
            reverse_code=remove_intelligence_catalog,
        ),
    ]
