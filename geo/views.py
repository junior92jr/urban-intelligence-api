from typing import override

from django.db.models import QuerySet
from rest_framework import mixins, viewsets

from geo.models import Country, ServiceArea
from geo.serializers import CountrySerializer, ServiceAreaSerializer


class CountryViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet[Country],
):
    serializer_class = CountrySerializer

    @override
    def get_queryset(self) -> QuerySet[Country]:
        return Country.objects.filter(is_active=True)


class ServiceAreaViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet[ServiceArea],
):
    serializer_class = ServiceAreaSerializer

    @override
    def get_queryset(self) -> QuerySet[ServiceArea]:
        queryset = (
            ServiceArea.objects.active()
            .select_related("country")
            .filter(
                country__is_active=True,
            )
        )
        country_code = self.request.query_params.get("country")
        if country_code:
            queryset = queryset.filter(country__code__iexact=country_code)

        return queryset
