from django.utils import timezone

from intelligence.models import IntelligenceImport


class IntelligenceProviderUnavailable(Exception):
    """Raised when an intelligence provider cannot be reached temporarily."""


class IntelligenceImporterNotConfigured(Exception):
    """Raised until a dataset has an implementation-specific importer."""


def run_intelligence_import(intelligence_import: IntelligenceImport) -> int:
    intelligence_import.status = IntelligenceImport.Status.RUNNING
    intelligence_import.started_at = timezone.now()
    intelligence_import.error_message = ""
    intelligence_import.save(
        update_fields=[
            "status",
            "started_at",
            "error_message",
            "updated_at",
        ],
    )

    raise IntelligenceImporterNotConfigured(
        f"No importer is configured for {intelligence_import.dataset}."
    )


def fail_intelligence_import(
    intelligence_import: IntelligenceImport,
    error: Exception,
) -> None:
    intelligence_import.status = IntelligenceImport.Status.FAILED
    intelligence_import.completed_at = timezone.now()
    intelligence_import.error_message = str(error)
    intelligence_import.save(
        update_fields=[
            "status",
            "completed_at",
            "error_message",
            "updated_at",
        ],
    )
