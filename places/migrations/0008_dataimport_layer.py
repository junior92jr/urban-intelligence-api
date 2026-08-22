from django.db import migrations, models

GROUP_TO_LAYER = {
    "food": "amenities",
    "essentials": "daily_life",
    "mobility": "mobility",
    "tourism": "green",
}


def migrate_category_groups_to_layers(apps, schema_editor):
    data_import = apps.get_model("places", "DataImport")

    for category_group, layer in GROUP_TO_LAYER.items():
        data_import.objects.filter(category_group=category_group).update(layer=layer)


class Migration(migrations.Migration):
    dependencies = [  # noqa: RUF012
        ("places", "0007_area_intelligence"),
    ]

    operations = [  # noqa: RUF012
        migrations.AddField(
            model_name="dataimport",
            name="layer",
            field=models.CharField(
                choices=[
                    ("amenities", "Amenities"),
                    ("daily_life", "Daily life"),
                    ("mobility", "Mobility"),
                    ("green", "Green spaces"),
                ],
                default="amenities",
                max_length=32,
            ),
        ),
        migrations.RunPython(
            migrate_category_groups_to_layers,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="dataimport",
            name="category_group",
        ),
    ]
