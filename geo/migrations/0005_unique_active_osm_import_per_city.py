from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [("geo", "0004_osm_import_run_city_scope")]  # noqa: RUF012

    operations = [  # noqa: RUF012
        migrations.AddConstraint(
            model_name="osmimportrun",
            constraint=models.UniqueConstraint(
                condition=Q(("city_slug__gt", ""), ("is_active", True)),
                fields=("city_slug",),
                name="unique_active_osm_import_per_city",
            ),
        ),
    ]
