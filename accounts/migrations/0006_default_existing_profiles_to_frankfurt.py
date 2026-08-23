from typing import Any

from django.db import migrations


def default_existing_profiles_to_frankfurt(apps: Any, schema_editor: Any) -> None:
    service_area_model = apps.get_model("geo", "ServiceArea")
    user_model = apps.get_model("accounts", "User")
    user_profile_model = apps.get_model("accounts", "UserProfile")

    frankfurt = service_area_model.objects.get(slug="frankfurt-am-main")

    for user in user_model.objects.iterator():
        profile, _created = user_profile_model.objects.get_or_create(user_id=user.pk)
        if profile.service_area_id == frankfurt.pk:
            continue

        profile.service_area_id = frankfurt.pk
        profile.save(update_fields=["service_area"])


class Migration(migrations.Migration):
    dependencies = [  # noqa: RUF012
        ("accounts", "0005_userprofile_realtime_refresh_enabled"),
        ("geo", "0002_seed_germany_service_area_boundaries"),
    ]

    operations = [  # noqa: RUF012
        migrations.RunPython(
            default_existing_profiles_to_frankfurt,
            migrations.RunPython.noop,
        ),
    ]
