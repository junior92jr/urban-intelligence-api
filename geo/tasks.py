from celery import shared_task

from geo.models import OsmImportRun
from geo.services.imports import fail_osm_import
from geo.services.imports import run_osm_import as run_osm_import_service


@shared_task(soft_time_limit=20 * 60, time_limit=25 * 60)  # type: ignore[untyped-decorator]
def run_osm_import(osm_import_run_id: int) -> None:
    osm_import_run = OsmImportRun.objects.get(pk=osm_import_run_id)
    try:
        run_osm_import_service(osm_import_run)
    except Exception as exc:
        fail_osm_import(osm_import_run, exc)
        raise
