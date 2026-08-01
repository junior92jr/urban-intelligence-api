import django.contrib.postgres.indexes
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import migrations, models

CATEGORY_GROUPS = {
    "bar": "food",
    "cafe": "food",
    "fast-food": "food",
    "pub": "food",
    "restaurant": "food",
    "bakery": "food",
    "pharmacy": "essentials",
    "supermarket": "essentials",
    "recycling": "essentials",
    "shelter": "essentials",
    "attraction": "tourism",
    "gallery": "tourism",
    "hotel": "tourism",
    "museum": "tourism",
    "garden": "tourism",
    "nature-reserve": "tourism",
    "park": "tourism",
    "pitch": "tourism",
    "memorial": "tourism",
    "wayside-shrine": "tourism",
    "protected-area": "tourism",
    "parking": "mobility",
    "beauty": "essentials",
    "clothes": "essentials",
    "dry-cleaning": "essentials",
    "jewelry": "essentials",
    "kiosk": "essentials",
}


def assign_category_groups(apps, schema_editor):
    place_category = apps.get_model("places", "PlaceCategory")

    for slug, group in CATEGORY_GROUPS.items():
        place_category.objects.filter(slug=slug).update(group=group)


def reset_category_groups(apps, schema_editor):
    place_category = apps.get_model("places", "PlaceCategory")
    place_category.objects.update(group="essentials")


class Migration(migrations.Migration):
    dependencies = [  # noqa: RUF012
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("geo", "0001_initial"),
        ("places", "0003_placecategory_include_in_default_search"),
    ]

    operations = [  # noqa: RUF012
        migrations.AddField(
            model_name="placecategory",
            name="group",
            field=models.CharField(
                choices=[
                    ("essentials", "Essentials"),
                    ("food", "Food"),
                    ("tourism", "Tourism"),
                    ("mobility", "Mobility"),
                ],
                default="essentials",
                max_length=32,
            ),
        ),
        migrations.RunPython(
            assign_category_groups,
            reverse_code=reset_category_groups,
        ),
        migrations.CreateModel(
            name="AreaScan",
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
                ("center", gis_models.PointField(srid=4326)),
                ("radius", models.PositiveIntegerField()),
                (
                    "category_group",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("essentials", "Essentials"),
                            ("food", "Food"),
                            ("tourism", "Tourism"),
                            ("mobility", "Mobility"),
                        ],
                        max_length=32,
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
                ("result_count", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "service_area",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="area_scans",
                        to="geo.servicearea",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="area_scans",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
                "indexes": [
                    django.contrib.postgres.indexes.GistIndex(
                        fields=["center"],
                        name="area_scan_center_gist",
                    ),
                    models.Index(
                        fields=["service_area", "status"],
                        name="area_scan_area_status_idx",
                    ),
                    models.Index(
                        fields=["created_at"], name="area_scan_created_at_idx"
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="DiscoveredPlace",
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
                ("osm_uid", models.CharField(max_length=128)),
                ("osm_id", models.BigIntegerField()),
                ("osm_type", models.CharField(max_length=32)),
                ("name", models.CharField(max_length=255)),
                ("category", models.CharField(max_length=100)),
                ("category_name", models.CharField(max_length=255)),
                ("category_group", models.CharField(max_length=32)),
                ("location", gis_models.PointField(srid=4326)),
                ("address", models.CharField(blank=True, max_length=500)),
                ("website", models.URLField(blank=True)),
                ("opening_hours", models.CharField(blank=True, max_length=255)),
                ("tags", models.JSONField(blank=True, default=dict)),
                (
                    "source",
                    models.CharField(
                        choices=[("open_street_map", "OpenStreetMap")],
                        default="open_street_map",
                        max_length=32,
                    ),
                ),
                ("fetched_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "service_area",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="discovered_places",
                        to="geo.servicearea",
                    ),
                ),
            ],
            options={
                "ordering": ("name",),
                "indexes": [
                    django.contrib.postgres.indexes.GistIndex(
                        fields=["location"],
                        name="discovered_place_location_gist",
                    ),
                    models.Index(
                        fields=["service_area", "category"],
                        name="disc_place_area_cat_idx",
                    ),
                    models.Index(
                        fields=["service_area", "category_group"],
                        name="disc_place_area_group_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("service_area", "osm_uid"),
                        name="unique_discovered_place_per_service_area",
                    ),
                ],
            },
        ),
    ]
