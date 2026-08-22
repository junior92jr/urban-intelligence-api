from typing import Any

from django.db import migrations

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


def seed_intelligence_catalog(apps: Any, schema_editor: Any) -> None:
    indicator = apps.get_model("intelligence", "IntelligenceIndicator")
    source = apps.get_model("intelligence", "IntelligenceSource")

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


class Migration(migrations.Migration):
    dependencies = [  # noqa: RUF012
        ("intelligence", "0001_initial"),
    ]

    operations = [  # noqa: RUF012
        migrations.RunPython(
            seed_intelligence_catalog, reverse_code=migrations.RunPython.noop
        ),
    ]
