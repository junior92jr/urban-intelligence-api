from typing import Any

import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.contrib.gis.geos import Point
from django.db import migrations, models

GERMANY_CITIES = [
    ("berlin", "Berlin", 52.52, 13.405, 3_755_251),
    ("hamburg", "Hamburg", 53.5511, 9.9937, 1_892_122),
    ("munich", "Munich", 48.1372, 11.5755, 1_512_491),
    ("cologne", "Cologne", 50.9375, 6.9603, 1_084_831),
    ("frankfurt-am-main", "Frankfurt am Main", 50.1109, 8.6821, 773_068),
    ("dusseldorf", "Düsseldorf", 51.2277, 6.7735, 629_047),
    ("leipzig", "Leipzig", 51.3397, 12.3731, 616_093),
    ("dresden", "Dresden", 51.0504, 13.7373, 563_311),
    ("nuremberg", "Nuremberg", 49.4521, 11.0767, 544_414),
    ("heidelberg", "Heidelberg", 49.3988, 8.6724, 162_273),
]


def seed_germany_service_areas(apps: Any, schema_editor: Any) -> None:
    country_model = apps.get_model("geo", "Country")
    service_area_model = apps.get_model("geo", "ServiceArea")

    germany, _ = country_model.objects.update_or_create(
        code="DE",
        defaults={
            "name": "Germany",
            "default_language": "de",
            "timezone": "Europe/Berlin",
            "currency": "EUR",
            "is_active": True,
            "sort_order": 10,
            "data_config": {
                "osm_country_code": "de",
                "supported_sources": ["open_street_map"],
            },
        },
    )

    for sort_order, (slug, name, latitude, longitude, population) in enumerate(
        GERMANY_CITIES,
        start=10,
    ):
        service_area_model.objects.update_or_create(
            country=germany,
            slug=slug,
            defaults={
                "name": name,
                "area_type": "city",
                "center": Point(longitude, latitude, srid=4326),
                "population": population,
                "timezone": "Europe/Berlin",
                "source": "curated",
                "source_id": f"de-{slug}",
                "is_active": True,
                "sort_order": sort_order,
                "data_config": {
                    "osm_country_code": "de",
                    "import_scope": "city",
                },
            },
        )


def remove_germany_service_areas(apps: Any, schema_editor: Any) -> None:
    country_model = apps.get_model("geo", "Country")
    country_model.objects.filter(code="DE").delete()


class Migration(migrations.Migration):
    initial = True

    dependencies = []  # noqa: RUF012

    operations = [  # noqa: RUF012
        migrations.CreateModel(
            name="Country",
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
                ("code", models.CharField(max_length=2, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("default_language", models.CharField(blank=True, max_length=16)),
                ("timezone", models.CharField(blank=True, max_length=64)),
                ("currency", models.CharField(blank=True, max_length=3)),
                ("data_config", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name_plural": "countries",
                "ordering": ("sort_order", "name"),
            },
        ),
        migrations.CreateModel(
            name="ServiceArea",
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
                (
                    "area_type",
                    models.CharField(
                        choices=[
                            ("city", "City"),
                            ("district", "District"),
                            ("region", "Region"),
                        ],
                        default="city",
                        max_length=32,
                    ),
                ),
                (
                    "center",
                    django.contrib.gis.db.models.fields.PointField(srid=4326),
                ),
                (
                    "boundary",
                    django.contrib.gis.db.models.fields.MultiPolygonField(
                        blank=True,
                        null=True,
                        srid=4326,
                    ),
                ),
                (
                    "bbox",
                    django.contrib.gis.db.models.fields.PolygonField(
                        blank=True,
                        null=True,
                        srid=4326,
                    ),
                ),
                ("population", models.PositiveIntegerField(blank=True, null=True)),
                ("timezone", models.CharField(blank=True, max_length=64)),
                ("data_config", models.JSONField(blank=True, default=dict)),
                ("source", models.CharField(blank=True, max_length=120)),
                ("source_id", models.CharField(blank=True, max_length=120)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                (
                    "country",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="service_areas",
                        to="geo.country",
                    ),
                ),
            ],
            options={
                "ordering": ("country__sort_order", "sort_order", "name"),
                "constraints": [
                    models.UniqueConstraint(
                        fields=("country", "slug"),
                        name="unique_service_area_slug_per_country",
                    ),
                ],
            },
        ),
        migrations.RunPython(
            seed_germany_service_areas,
            remove_germany_service_areas,
        ),
    ]
