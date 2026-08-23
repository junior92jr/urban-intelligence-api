from typing import Any, cast

from celery import Task, shared_task

from intelligence.models import IntelligenceImport
from intelligence.services.imports import (
    IntelligenceImportConfigurationError,
    IntelligenceImporterNotConfigured,
    IntelligenceProviderUnavailable,
    fail_intelligence_import,
)
from intelligence.services.imports import (
    run_intelligence_import as run_intelligence_import_service,
)

MAX_INTELLIGENCE_IMPORT_RETRIES = 3


def retry_delay(retries: int) -> int:
    return int(min(30 * (2**retries), 300))


@shared_task(bind=True)  # type: ignore[untyped-decorator]
def run_intelligence_import(self: Task, intelligence_import_id: int) -> None:
    intelligence_import = IntelligenceImport.objects.select_related(
        "dataset",
        "dataset__source",
        "dataset__indicator",
        "service_area",
    ).get(pk=intelligence_import_id)

    try:
        run_intelligence_import_service(intelligence_import)
    except IntelligenceProviderUnavailable as exc:
        if self.request.retries < MAX_INTELLIGENCE_IMPORT_RETRIES:
            intelligence_import.status = IntelligenceImport.Status.PENDING
            intelligence_import.error_message = (
                "Provider is unavailable. Retrying soon."
            )
            intelligence_import.save(
                update_fields=["status", "error_message", "updated_at"]
            )
            raise cast(Any, self).retry(
                exc=exc,
                countdown=retry_delay(self.request.retries),
            ) from exc

        fail_intelligence_import(intelligence_import, exc)
        raise
    except (
        IntelligenceImportConfigurationError,
        IntelligenceImporterNotConfigured,
    ) as exc:
        fail_intelligence_import(intelligence_import, exc)
    except Exception as exc:
        fail_intelligence_import(intelligence_import, exc)
        raise
