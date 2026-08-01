from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [  # noqa: RUF012
        ("places", "0004_category_groups_and_place_discovery"),
    ]

    operations = [  # noqa: RUF012
        migrations.AddField(
            model_name="areascan",
            name="category",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
