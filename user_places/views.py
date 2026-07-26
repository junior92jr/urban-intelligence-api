from typing import cast, override

from django.db.models import QuerySet
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from accounts.models import User
from user_places.models import FavoritePlace
from user_places.serializers import FavoritePlaceSerializer


class FavoritePlaceListCreateView(generics.ListCreateAPIView[FavoritePlace]):
    serializer_class = FavoritePlaceSerializer
    permission_classes = (IsAuthenticated,)

    @override
    def get_queryset(self) -> QuerySet[FavoritePlace]:
        return FavoritePlace.objects.filter(user=cast(User, self.request.user))


class FavoritePlaceDestroyView(generics.DestroyAPIView[FavoritePlace]):
    lookup_field = "osm_uid"
    serializer_class = FavoritePlaceSerializer
    permission_classes = (IsAuthenticated,)

    @override
    def get_queryset(self) -> QuerySet[FavoritePlace]:
        return FavoritePlace.objects.filter(user=cast(User, self.request.user))
