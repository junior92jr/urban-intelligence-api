from typing import Any, cast

from celery import Task, shared_task

from places.models import AreaScan, DataImport
from places.services.discovery import (
    fail_data_import,
    fail_scan,
    run_scan,
)
from places.services.discovery import (
    run_data_import as run_data_import_service,
)
from places.services.open_street_map import OpenStreetMapResourceUnavailable

MAX_OPEN_STREET_MAP_RETRIES = 3


def retry_delay(retries: int) -> int:
    return int(min(30 * (2**retries), 300))


@shared_task(bind=True)  # type: ignore[untyped-decorator]
def run_area_scan(self: Task, scan_id: int) -> None:
    scan = AreaScan.objects.select_related("service_area").get(pk=scan_id)

    try:
        run_scan(scan)
    except OpenStreetMapResourceUnavailable as exc:
        if self.request.retries < MAX_OPEN_STREET_MAP_RETRIES:
            scan.status = AreaScan.Status.PENDING
            scan.error_message = "OpenStreetMap is unavailable. Retrying soon."
            scan.save(update_fields=["status", "error_message", "updated_at"])
            raise cast(Any, self).retry(
                exc=exc,
                countdown=retry_delay(self.request.retries),
            ) from exc

        fail_scan(scan, exc)
        raise
    except Exception as exc:
        fail_scan(scan, exc)
        raise


@shared_task(bind=True)  # type: ignore[untyped-decorator]
def run_data_import(self: Task, data_import_id: int) -> None:
    data_import = DataImport.objects.select_related("service_area").get(
        pk=data_import_id,
    )

    try:
        run_data_import_service(data_import)
    except OpenStreetMapResourceUnavailable as exc:
        if self.request.retries < MAX_OPEN_STREET_MAP_RETRIES:
            data_import.status = DataImport.Status.PENDING
            data_import.error_message = "OpenStreetMap is unavailable. Retrying soon."
            data_import.save(update_fields=["status", "error_message", "updated_at"])
            raise cast(Any, self).retry(
                exc=exc,
                countdown=retry_delay(self.request.retries),
            ) from exc

        fail_data_import(data_import, exc)
        raise
    except Exception as exc:
        fail_data_import(data_import, exc)
        raise
