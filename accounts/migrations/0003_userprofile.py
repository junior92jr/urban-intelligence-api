import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [  # noqa: RUF012
        ("accounts", "0002_alter_accounttoken_options_alter_user_options_and_more"),
    ]

    operations = [  # noqa: RUF012
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("country", models.CharField(blank=True, max_length=120)),
                ("city", models.CharField(blank=True, max_length=120)),
                ("address", models.CharField(blank=True, max_length=255)),
                (
                    "default_location",
                    django.contrib.gis.db.models.fields.PointField(
                        blank=True,
                        null=True,
                        srid=4326,
                    ),
                ),
                (
                    "default_location_label",
                    models.CharField(blank=True, max_length=255),
                ),
                ("location_sharing_enabled", models.BooleanField(default=False)),
                ("preferred_radius", models.PositiveIntegerField(default=500)),
                (
                    "onboarding_completed_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("user__email",),
            },
        ),
    ]
