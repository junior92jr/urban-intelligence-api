from typing import Any

import django.db.models.deletion
from django.db import migrations, models


def move_profile_city_to_service_area(apps: Any, schema_editor: Any) -> None:
    service_area_model = apps.get_model("geo", "ServiceArea")
    user_profile_model = apps.get_model("accounts", "UserProfile")

    fallback_service_area = service_area_model.objects.filter(
        slug="frankfurt-am-main",
    ).first()
    if fallback_service_area is None:
        return

    city_slug_map = {
        "berlin": "berlin",
        "hamburg": "hamburg",
        "munich": "munich",
        "münchen": "munich",
        "cologne": "cologne",
        "köln": "cologne",
        "frankfurt": "frankfurt-am-main",
        "frankfurt am main": "frankfurt-am-main",
        "düsseldorf": "dusseldorf",
        "dusseldorf": "dusseldorf",
        "leipzig": "leipzig",
        "dresden": "dresden",
        "nuremberg": "nuremberg",
        "nürnberg": "nuremberg",
        "heidelberg": "heidelberg",
    }

    service_areas = {
        service_area.slug: service_area
        for service_area in service_area_model.objects.filter(country__code="DE")
    }
    for profile in user_profile_model.objects.all():
        city = (profile.city or "").strip().lower()
        service_area = service_areas.get(city_slug_map.get(city, ""))
        profile.service_area = service_area or fallback_service_area
        profile.save(update_fields=["service_area"])


class Migration(migrations.Migration):
    dependencies = [  # noqa: RUF012
        ("geo", "0001_initial"),
        ("accounts", "0003_userprofile"),
    ]

    operations = [  # noqa: RUF012
        migrations.AddField(
            model_name="userprofile",
            name="service_area",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="user_profiles",
                to="geo.servicearea",
            ),
        ),
        migrations.RunPython(
            move_profile_city_to_service_area,
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="address",
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="city",
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="country",
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="default_location_label",
        ),
    ]
