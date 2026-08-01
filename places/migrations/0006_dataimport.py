import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [  # noqa: RUF012
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("geo", "0001_initial"),
        ("places", "0005_areascan_category"),
    ]

    operations = [  # noqa: RUF012
        migrations.CreateModel(
            name="DataImport",
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
                    "source",
                    models.CharField(
                        choices=[("open_street_map", "OpenStreetMap")],
                        default="open_street_map",
                        max_length=32,
                    ),
                ),
                (
                    "category_group",
                    models.CharField(
                        choices=[
                            ("essentials", "Essentials"),
                            ("food", "Food"),
                            ("tourism", "Tourism"),
                            ("mobility", "Mobility"),
                        ],
                        max_length=32,
                    ),
                ),
                ("radius", models.PositiveIntegerField(default=8000)),
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
                ("result_count", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "requested_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="requested_data_imports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "service_area",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="data_imports",
                        to="geo.servicearea",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
                "indexes": [
                    models.Index(
                        fields=["source", "service_area", "status"],
                        name="data_import_source_area_idx",
                    ),
                    models.Index(
                        fields=["created_at"],
                        name="data_import_created_idx",
                    ),
                ],
            },
        ),
    ]
