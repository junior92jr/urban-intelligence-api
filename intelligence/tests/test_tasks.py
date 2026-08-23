from typing import Any, cast

import pytest
from chainmock import mocker

from geo.models import ServiceArea
from intelligence import tasks
from intelligence.models import IntelligenceDataset, IntelligenceImport
from intelligence.services.imports import IntelligenceImportConfigurationError

pytestmark = pytest.mark.django_db


def test_task_marks_configuration_error_as_failed_without_reraising() -> None:
    intelligence_import = IntelligenceImport.objects.create(
        dataset=IntelligenceDataset.objects.get(slug="tree-cover-density-100m"),
        service_area=ServiceArea.objects.get(slug="frankfurt-am-main"),
    )
    mocker(tasks).mock("run_intelligence_import_service").side_effect(
        IntelligenceImportConfigurationError("Reference date is not configured.")
    )

    cast(Any, tasks.run_intelligence_import).run(intelligence_import.pk)

    intelligence_import.refresh_from_db()
    assert intelligence_import.status == IntelligenceImport.Status.FAILED
    assert intelligence_import.error_message == "Reference date is not configured."
