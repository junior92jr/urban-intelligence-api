import pytest

from geo.models import ServiceArea
from intelligence.models import (
    IntelligenceDataset,
    IntelligenceImport,
    IntelligenceIndicator,
    IntelligenceSource,
)
from intelligence.services.imports import (
    IntelligenceImporterNotConfigured,
    run_intelligence_import,
)

pytestmark = pytest.mark.django_db


def test_run_intelligence_import_marks_job_running_before_provider_dispatch() -> None:
    dataset = IntelligenceDataset.objects.create(
        source=IntelligenceSource.objects.get(slug="open-street-map"),
        indicator=IntelligenceIndicator.objects.get(slug="green-exposure"),
        slug="tree-cover-density",
        name="Tree Cover Density",
    )
    intelligence_import = IntelligenceImport.objects.create(
        dataset=dataset,
        service_area=ServiceArea.objects.get(slug="frankfurt-am-main"),
    )

    with pytest.raises(IntelligenceImporterNotConfigured):
        run_intelligence_import(intelligence_import)

    intelligence_import.refresh_from_db()
    assert intelligence_import.status == IntelligenceImport.Status.RUNNING
    assert intelligence_import.started_at is not None
