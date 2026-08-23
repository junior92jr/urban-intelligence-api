from typing import Any

from django.db import migrations, models

COPERNICUS_SOURCE = {
    "slug": "copernicus-land-monitoring",
    "name": "Copernicus Land Monitoring Service",
    "attribution": "Copernicus Land Monitoring Service",
    "website": "https://land.copernicus.eu",
    "is_active": True,
    "sort_order": 10,
}

TREE_COVER_DENSITY_DATASET = {
    "slug": "tree-cover-density-100m",
    "name": "Tree Cover Density (100 m)",
    "reference_url": (
        "https://land.copernicus.eu/en/products/high-resolution-layer-"
        "forests-and-tree-cover/tree-cover-density-2018-present-raster-100m-"
        "europe-yearly"
    ),
    "is_active": True,
    "sort_order": 10,
}


def seed_copernicus_tree_cover_density(apps: Any, schema_editor: Any) -> None:
    source_model = apps.get_model("intelligence", "IntelligenceSource")
    indicator_model = apps.get_model("intelligence", "IntelligenceIndicator")
    dataset_model = apps.get_model("intelligence", "IntelligenceDataset")

    source, _created = source_model.objects.update_or_create(
        slug=COPERNICUS_SOURCE["slug"],
        defaults={
            key: value for key, value in COPERNICUS_SOURCE.items() if key != "slug"
        },
    )
    indicator = indicator_model.objects.get(slug="green-exposure")
    dataset_model.objects.update_or_create(
        source=source,
        slug=TREE_COVER_DENSITY_DATASET["slug"],
        defaults={
            **{
                key: value
                for key, value in TREE_COVER_DENSITY_DATASET.items()
                if key != "slug"
            },
            "indicator": indicator,
        },
    )


class Migration(migrations.Migration):
    dependencies = [  # noqa: RUF012
        ("intelligence", "0002_imports"),
    ]

    operations = [  # noqa: RUF012
        migrations.AddConstraint(
            model_name="areaindicatorobservation",
            constraint=models.UniqueConstraint(
                fields=("service_area", "indicator", "source", "observed_at"),
                name="area_indicator_source_date_uq",
            ),
        ),
        migrations.RunPython(
            seed_copernicus_tree_cover_density,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
