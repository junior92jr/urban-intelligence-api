from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("geo", "0003_service_area_osm_versioning")]  # noqa: RUF012

    operations = [  # noqa: RUF012
        migrations.AddField(
            model_name="osmimportrun",
            name="city_slug",
            field=models.SlugField(default=""),
            preserve_default=False,
        ),
        migrations.AddIndex(
            model_name="osmimportrun",
            index=models.Index(
                fields=["city_slug", "is_active"], name="osm_import_city_idx"
            ),
        ),
    ]
