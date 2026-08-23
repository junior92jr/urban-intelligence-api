import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [  # noqa: RUF012
        ("geo", "0001_initial"),
        ("intelligence", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [  # noqa: RUF012
        migrations.CreateModel(
            name="IntelligenceDataset",
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
                ("slug", models.SlugField()),
                ("name", models.CharField(max_length=160)),
                ("reference_url", models.URLField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                (
                    "indicator",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="datasets",
                        to="intelligence.intelligenceindicator",
                    ),
                ),
                (
                    "source",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="datasets",
                        to="intelligence.intelligencesource",
                    ),
                ),
            ],
            options={
                "ordering": ("source__sort_order", "sort_order", "name"),
            },
        ),
        migrations.CreateModel(
            name="IntelligenceImport",
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
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=32,
                    ),
                ),
                ("dataset_version", models.CharField(blank=True, max_length=100)),
                ("reference_date", models.DateField(blank=True, null=True)),
                ("result_count", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dataset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="imports",
                        to="intelligence.intelligencedataset",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="requested_intelligence_imports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "service_area",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="intelligence_imports",
                        to="geo.servicearea",
                    ),
                ),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddConstraint(
            model_name="intelligencedataset",
            constraint=models.UniqueConstraint(
                fields=("source", "slug"),
                name="unique_intelligence_dataset_per_source",
            ),
        ),
        migrations.AddIndex(
            model_name="intelligenceimport",
            index=models.Index(
                fields=["dataset", "service_area", "status"],
                name="intel_import_dataset_area_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="intelligenceimport",
            index=models.Index(
                fields=["created_at"],
                name="intel_import_created_idx",
            ),
        ),
    ]
