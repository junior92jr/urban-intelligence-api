import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from geo.models import ServiceArea
from intelligence.models import (
    AreaIndicatorObservation,
    IntelligenceIndicator,
    IntelligenceSource,
)

pytestmark = pytest.mark.django_db


def test_intelligence_catalog_contains_the_area_indicator_groups() -> None:
    assert set(IntelligenceIndicator.objects.values_list("group", flat=True)) == {
        "mobility",
        "urban_environment",
        "daily_life",
        "dynamics",
    }
    assert IntelligenceIndicator.objects.get(slug="walkability").value_type == "score"
    assert (
        IntelligenceIndicator.objects.get(slug="construction-activity").value_type
        == "trend"
    )
    assert (
        IntelligenceSource.objects.get(slug="open-street-map").name == "OpenStreetMap"
    )


def test_area_indicator_observation_supports_scores_and_trends() -> None:
    observation = AreaIndicatorObservation(
        service_area=ServiceArea.objects.get(slug="frankfurt-am-main"),
        indicator=IntelligenceIndicator.objects.get(slug="walkability"),
        source=IntelligenceSource.objects.get(slug="open-street-map"),
        score=88,
        methodology="Pedestrian network coverage",
        observed_at=timezone.now(),
    )

    observation.full_clean()
    observation.save()

    assert observation.score == 88
    assert observation.trend == ""


def test_area_indicator_observation_requires_a_score_or_trend() -> None:
    observation = AreaIndicatorObservation(
        service_area=ServiceArea.objects.get(slug="frankfurt-am-main"),
        indicator=IntelligenceIndicator.objects.get(slug="traffic"),
        source=IntelligenceSource.objects.get(slug="frankfurt-open-data"),
        observed_at=timezone.now(),
    )

    with pytest.raises(ValidationError):
        observation.full_clean()
