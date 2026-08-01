from typing import Any, cast, override

from django.contrib.auth.models import AbstractBaseUser
from django.db.models import QuerySet
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.models import User, UserProfile
from user_places.services import record_place_search

from .models import AreaScan, PlaceCategory
from .serializers import (
    AreaScanCreateSerializer,
    AreaScanSerializer,
    CategorySerializer,
    DiscoveredPlaceSerializer,
    NearbyPlacesQuerySerializer,
    RecommendationsQuerySerializer,
)
from .services import search_places_by_location
from .services.discovery import create_area_scan, nearby_places
from .tasks import run_area_scan


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


class NearbyPlacesView(GenericAPIView[Any]):
    serializer_class = NearbyPlacesQuerySerializer
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        serializer = cast(
            NearbyPlacesQuerySerializer,
            self.get_serializer(data=request.query_params),
        )
        serializer.is_valid(raise_exception=True)
        query_params = serializer.to_query_params()
        places = nearby_places(
            latitude=query_params["lat"],
            longitude=query_params["lng"],
            radius=query_params["search_radius"],
            category=query_params.get("category"),
        )
        response_serializer = DiscoveredPlaceSerializer(places, many=True)

        return Response({"places": response_serializer.data})


class AreaScanCreateView(GenericAPIView[Any]):
    serializer_class = AreaScanCreateSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request: Request) -> Response:
        serializer = cast(
            AreaScanCreateSerializer,
            self.get_serializer(data=request.data),
        )
        serializer.is_valid(raise_exception=True)
        query_params = serializer.to_query_params()
        user = request.user
        assert isinstance(user, AbstractBaseUser)
        profile = UserProfile.get_for_user(user)

        if profile.service_area is None:
            raise ValidationError(
                {"service_area": "Complete onboarding before scanning places."}
            )

        scan = create_area_scan(
            service_area=profile.service_area,
            latitude=query_params["lat"],
            longitude=query_params["lng"],
            radius=query_params["search_radius"],
            user_id=user.pk,
            category=query_params.get("category"),
        )
        assert scan.pk is not None
        cast(Any, run_area_scan).delay(scan.pk)

        return Response(AreaScanSerializer(scan).data, status=status.HTTP_202_ACCEPTED)


class AreaScanDetailView(RetrieveAPIView[AreaScan]):
    serializer_class = AreaScanSerializer
    permission_classes = (IsAuthenticated,)

    @override
    def get_queryset(self) -> QuerySet[AreaScan]:
        user = self.request.user
        if not isinstance(user, User):
            return AreaScan.objects.none()

        return AreaScan.objects.filter(user=user)
