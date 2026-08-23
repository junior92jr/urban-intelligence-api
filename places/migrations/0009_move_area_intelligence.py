from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [  # noqa: RUF012
        ("places", "0008_dataimport_layer"),
    ]

    operations = [  # noqa: RUF012
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="AreaIndicatorObservation"),
                migrations.DeleteModel(name="IntelligenceIndicator"),
                migrations.DeleteModel(name="IntelligenceSource"),
            ],
        ),
    ]
