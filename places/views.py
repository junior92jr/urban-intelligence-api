from typing import Any, cast, override

from django.db.models import QuerySet
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.models import User
from user_places.services import record_place_search

from .models import PlaceCategory
from .serializers import CategorySerializer, RecommendationsQuerySerializer
from .services import search_places_by_location


class RecommendationViewSet(viewsets.GenericViewSet[Any]):
    """
    ViewSet that exposes OpenStreetMap place data.
    """

    serializer_class = RecommendationsQuerySerializer
    permission_classes = (IsAuthenticated,)
    queryset = None

    @action(methods=["get"], url_path=r"places", detail=False)
    def places(self, request: Request) -> Response:
        """
        Retrieve places near a location from OpenStreetMap.
        """

        serializer = cast(
            RecommendationsQuerySerializer,
            self.get_serializer(data=request.query_params),
        )
        serializer.is_valid(raise_exception=True)

        query_params = serializer.to_query_params()
        response = search_places_by_location(query_params)
        record_place_search(
            user=cast(User, request.user),
            latitude=query_params["lat"],
            longitude=query_params["lng"],
            search_radius=query_params["search_radius"],
            category=query_params.get("category", ""),
            result_count=len(response.places),
        )

        return Response(response.model_dump(by_alias=True, exclude_none=True))


class CategoryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet[PlaceCategory]):
    """
    ViewSet that exposes active place categories.
    """

    serializer_class = CategorySerializer
    permission_classes = (AllowAny,)

    @override
    def get_queryset(self) -> QuerySet[PlaceCategory]:
        return PlaceCategory.objects.filter(is_active=True).order_by(
            "sort_order",
            "name",
        )
