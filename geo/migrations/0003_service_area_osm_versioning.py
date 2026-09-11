from typing import Any

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


def normalize_existing_service_area_sources(apps: Any, schema_editor: Any) -> None:
    """Treat pre-versioned curated rows as manual records during the transition."""
    service_area_model = apps.get_model("geo", "ServiceArea")
    service_area_model.objects.exclude(source="osm").update(source="manual")


class Migration(migrations.Migration):
    dependencies = [  # noqa: RUF012
        ("geo", "0002_seed_germany_service_area_boundaries"),
    ]

    operations = [  # noqa: RUF012
        migrations.CreateModel(
            name="OsmImportRun",
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
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                            ("superseded", "Superseded"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("source_object_key", models.CharField(max_length=512)),
                ("source_sha256", models.CharField(blank=True, max_length=64)),
                ("source_timestamp", models.DateTimeField(blank=True, null=True)),
                ("current_stage", models.CharField(blank=True, max_length=120)),
                ("total_cities", models.PositiveIntegerField(default=0)),
                ("processed_cities", models.PositiveIntegerField(default=0)),
                ("error_summary", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=False)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ("-created_at",),
                "indexes": [
                    models.Index(
                        fields=["status", "is_active"],
                        name="osm_import_status_idx",
                    ),
                ],
            },
        ),
        migrations.AddField(
            model_name="servicearea",
            name="import_run",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="service_areas",
                to="geo.osmimportrun",
            ),
        ),
        migrations.AddField(
            model_name="servicearea",
            name="osm_admin_level",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="servicearea",
            name="osm_element_type",
            field=models.CharField(
                blank=True,
                choices=[("node", "Node"), ("way", "Way"), ("relation", "Relation")],
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="servicearea",
            name="osm_tags",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="servicearea",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="children",
                to="geo.servicearea",
            ),
        ),
        migrations.AlterField(
            model_name="servicearea",
            name="area_type",
            field=models.CharField(
                choices=[
                    ("region", "Region"),
                    ("city", "City"),
                    ("district", "District"),
                    ("neighborhood", "Neighborhood"),
                ],
                default="city",
                max_length=32,
            ),
        ),
        migrations.RunPython(
            normalize_existing_service_area_sources,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="servicearea",
            name="source",
            field=models.CharField(
                choices=[("manual", "Manual"), ("osm", "OpenStreetMap")],
                default="manual",
                max_length=32,
            ),
        ),
        migrations.AddConstraint(
            model_name="servicearea",
            constraint=models.UniqueConstraint(
                condition=Q(
                    ("osm_element_type__gt", ""),
                    ("source", "osm"),
                    ("source_id__gt", ""),
                ),
                fields=("import_run", "source", "osm_element_type", "source_id"),
                name="unique_osm_area_per_import",
            ),
        ),
        migrations.AddIndex(
            model_name="servicearea",
            index=models.Index(
                fields=["country", "area_type", "is_active"],
                name="service_area_lookup_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="servicearea",
            index=models.Index(
                fields=["parent", "area_type"],
                name="service_area_parent_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="servicearea",
            index=models.Index(
                fields=["import_run", "area_type"],
                name="service_area_import_idx",
            ),
        ),
    ]
