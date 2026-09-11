from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("geo", "0005_unique_active_osm_import_per_city")]  # noqa: RUF012

    operations = [  # noqa: RUF012
        migrations.AlterField(
            model_name="servicearea",
            name="slug",
            field=models.SlugField(max_length=250),
        ),
    ]
