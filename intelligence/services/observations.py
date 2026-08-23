from collections.abc import Iterable

from geo.models import ServiceArea
from intelligence.models import AreaIndicatorObservation, IntelligenceIndicator


def get_area_intelligence(
    *,
    service_area: ServiceArea,
) -> list[tuple[IntelligenceIndicator, AreaIndicatorObservation | None]]:
    indicators = IntelligenceIndicator.objects.filter(is_active=True).order_by(
        "group",
        "sort_order",
        "name",
    )
    observations = (
        AreaIndicatorObservation.objects.filter(
            service_area=service_area,
        )
        .select_related("source", "indicator")
        .order_by("indicator_id", "-observed_at")
    )

    latest_observations = latest_by_indicator(observations)

    return [
        (indicator, latest_observations.get(indicator.pk)) for indicator in indicators
    ]


def latest_by_indicator(
    observations: Iterable[AreaIndicatorObservation],
) -> dict[int, AreaIndicatorObservation]:
    latest: dict[int, AreaIndicatorObservation] = {}

    for observation in observations:
        assert observation.indicator.pk is not None
        latest.setdefault(observation.indicator.pk, observation)

    return latest
