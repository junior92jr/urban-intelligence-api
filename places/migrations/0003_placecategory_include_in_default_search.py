from django.db import migrations, models

DEFAULT_SEARCH_CATEGORY_SLUGS = (
    "restaurant",
    "cafe",
    "bar",
    "pub",
    "museum",
    "attraction",
    "park",
    "hotel",
    "pharmacy",
    "parking",
)


def include_default_search_categories(apps, schema_editor):
    place_category = apps.get_model("places", "PlaceCategory")
    place_category.objects.filter(slug__in=DEFAULT_SEARCH_CATEGORY_SLUGS).update(
        include_in_default_search=True,
    )


def remove_default_search_categories(apps, schema_editor):
    place_category = apps.get_model("places", "PlaceCategory")
    place_category.objects.filter(slug__in=DEFAULT_SEARCH_CATEGORY_SLUGS).update(
        include_in_default_search=False,
    )


class Migration(migrations.Migration):
    dependencies = [  # noqa: RUF012
        ("places", "0002_seed_place_categories"),
    ]

    operations = [  # noqa: RUF012
        migrations.AddField(
            model_name="placecategory",
            name="include_in_default_search",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            include_default_search_categories,
            reverse_code=remove_default_search_categories,
        ),
    ]
