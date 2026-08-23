import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [  # noqa: RUF012
        ("geo", "0001_initial"),
        ("places", "0009_move_area_intelligence"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [  # noqa: RUF012
        migrations.RenameModel(
            old_name="DataImport",
            new_name="PlaceImport",
        ),
        migrations.RemoveField(
            model_name="placeimport",
            name="source",
        ),
        migrations.AlterField(
            model_name="placeimport",
            name="requested_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="requested_place_imports",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="placeimport",
            name="service_area",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="place_imports",
                to="geo.servicearea",
            ),
        ),
        migrations.RemoveIndex(
            model_name="placeimport",
            name="data_import_source_area_idx",
        ),
        migrations.RemoveIndex(
            model_name="placeimport",
            name="data_import_created_idx",
        ),
        migrations.AddIndex(
            model_name="placeimport",
            index=models.Index(
                fields=["service_area", "status"],
                name="place_import_area_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="placeimport",
            index=models.Index(
                fields=["created_at"],
                name="place_import_created_idx",
            ),
        ),
    ]
