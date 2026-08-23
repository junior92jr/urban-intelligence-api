from datetime import date

from django.utils import timezone
from pydantic import BaseModel, ConfigDict

from intelligence.models import IntelligenceImport


class IntelligenceProviderUnavailable(Exception):
    """Raised when an intelligence provider cannot be reached temporarily."""


class IntelligenceImporterNotConfigured(Exception):
    """Raised until a dataset has an implementation-specific importer."""


class IntelligenceImportConfigurationError(Exception):
    """Raised when an enabled dataset is missing required import configuration."""


class IntelligenceImportResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    result_count: int
    dataset_version: str
    reference_date: date
    metadata: dict[str, object]


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

    result = dispatch_intelligence_import(intelligence_import)
    intelligence_import.status = IntelligenceImport.Status.COMPLETED
    intelligence_import.completed_at = timezone.now()
    intelligence_import.result_count = result.result_count
    intelligence_import.dataset_version = result.dataset_version
    intelligence_import.reference_date = result.reference_date
    intelligence_import.metadata = result.metadata
    intelligence_import.save(
        update_fields=[
            "status",
            "completed_at",
            "result_count",
            "dataset_version",
            "reference_date",
            "metadata",
            "updated_at",
        ],
    )

    return result.result_count


def dispatch_intelligence_import(
    intelligence_import: IntelligenceImport,
) -> IntelligenceImportResult:
    dataset = intelligence_import.dataset

    if (
        dataset.source.slug == "copernicus-land-monitoring"
        and dataset.slug == "tree-cover-density-100m"
    ):
        from intelligence.services.providers.copernicus import (
            import_tree_cover_density,
        )

        return import_tree_cover_density(intelligence_import)

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
