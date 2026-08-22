import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [  # noqa: RUF012
        ("geo", "0001_initial"),
        ("places", "0009_move_area_intelligence"),
    ]

    operations = [  # noqa: RUF012
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        'ALTER TABLE "places_intelligencesource" '
                        'RENAME TO "intelligence_intelligencesource";'
                    ),
                    reverse_sql=(
                        'ALTER TABLE "intelligence_intelligencesource" '
                        'RENAME TO "places_intelligencesource";'
                    ),
                ),
                migrations.RunSQL(
                    sql=(
                        'ALTER TABLE "places_intelligenceindicator" '
                        'RENAME TO "intelligence_intelligenceindicator";'
                    ),
                    reverse_sql=(
                        'ALTER TABLE "intelligence_intelligenceindicator" '
                        'RENAME TO "places_intelligenceindicator";'
                    ),
                ),
                migrations.RunSQL(
                    sql=(
                        'ALTER TABLE "places_areaindicatorobservation" '
                        'RENAME TO "intelligence_areaindicatorobservation";'
                    ),
                    reverse_sql=(
                        'ALTER TABLE "intelligence_areaindicatorobservation" '
                        'RENAME TO "places_areaindicatorobservation";'
                    ),
                ),
            ],
            state_operations=[
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
                                to="intelligence.intelligenceindicator",
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
                                to="intelligence.intelligencesource",
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
            ],
        ),
    ]
