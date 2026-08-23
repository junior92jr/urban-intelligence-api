import json
from pathlib import Path
from typing import Any

from django.contrib.gis.geos import GEOSGeometry
from django.db import migrations

BOUNDARIES_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "germany-city-boundaries-bkg-vg250-2026-01-01.geojson"
)
BOUNDARY_SOURCE = {
    "dataset": "BKG VG250",
    "license": "dl-de/by-2-0",
    "reference_date": "2026-01-01",
}


def seed_germany_service_area_boundaries(apps: Any, schema_editor: Any) -> None:
    service_area_model = apps.get_model("geo", "ServiceArea")
    boundary_collection = json.loads(BOUNDARIES_PATH.read_text())

    for feature in boundary_collection["features"]:
        properties = feature["properties"]
        boundary = GEOSGeometry(json.dumps(feature["geometry"]), srid=4326)
        data_config = {
            "osm_country_code": "de",
            "import_scope": "city",
            "boundary": {
                **BOUNDARY_SOURCE,
                "municipality_key": properties["municipality_key"],
                "source_name": properties["source_name"],
            },
        }
        service_area_model.objects.filter(
            country__code="DE",
            slug=properties["slug"],
        ).update(
            boundary=boundary,
            bbox=boundary.envelope,
            data_config=data_config,
        )


class Migration(migrations.Migration):
    dependencies = [  # noqa: RUF012
        ("geo", "0001_initial"),
    ]

    operations = [  # noqa: RUF012
        migrations.RunPython(
            seed_germany_service_area_boundaries, migrations.RunPython.noop
        ),
    ]
