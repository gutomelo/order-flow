from typing import Any

from django.db.models import Count, QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.identity.domain.permissions import Permission
from apps.pricing import services
from apps.pricing.api.serializers import (
    PriceListCreateSerializer,
    PriceListItemCreateSerializer,
    PriceListItemSerializer,
    PriceListItemUpdateSerializer,
    PriceListRenameSerializer,
    PriceListSerializer,
)
from apps.pricing.models import PriceList, PriceListItem
from shared.permissions import HasReadWritePermission
from shared.tenancy.api import TenantScopedQuerysetMixin

_PERMISSION = HasReadWritePermission(read=Permission.PRICING_READ, write=Permission.PRICING_MANAGE)


class PriceListViewSet(
    TenantScopedQuerysetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet[PriceList],
):
    queryset = PriceList.objects.select_related("segment").annotate(items_count=Count("items"))
    serializer_class = PriceListSerializer
    permission_classes = (IsAuthenticated, _PERMISSION)
    http_method_names = ("get", "post", "patch", "delete", "head", "options")
    pagination_class = None  # poucas tabelas por organização (uma padrão + uma por segmento)
    ordering = ("name",)

    @extend_schema(request=PriceListCreateSerializer, responses={201: PriceListSerializer})
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = PriceListCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        price_list = services.create_price_list(self.organization_id, **serializer.validated_data)
        return Response(PriceListSerializer(price_list).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=PriceListRenameSerializer, responses=PriceListSerializer)
    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        price_list = self.get_object()
        serializer = PriceListRenameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        price_list = services.rename_price_list(price_list, **serializer.validated_data)
        return Response(PriceListSerializer(price_list).data)

    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        services.delete_price_list(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)


class PriceListItemViewSet(
    TenantScopedQuerysetMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet[PriceListItem],
):
    """Itens de uma tabela; filtrados pela organização e pela tabela da URL (anti-IDOR)."""

    queryset = PriceListItem.objects.select_related("product")
    serializer_class = PriceListItemSerializer
    permission_classes = (IsAuthenticated, _PERMISSION)
    http_method_names = ("get", "post", "patch", "delete", "head", "options")
    search_fields = ("product__sku", "product__name")
    ordering = ("product__name",)

    def get_price_list(self) -> PriceList:
        return get_object_or_404(
            PriceList.objects.for_organization(self.organization_id),
            id=self.kwargs["price_list_pk"],
        )

    def get_queryset(self) -> QuerySet[PriceListItem]:
        return super().get_queryset().filter(price_list_id=self.kwargs["price_list_pk"])

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        self.get_price_list()  # tabela inexistente → 404, não lista vazia
        return super().list(request, *args, **kwargs)

    @extend_schema(request=PriceListItemCreateSerializer, responses={201: PriceListItemSerializer})
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        price_list = self.get_price_list()
        serializer = PriceListItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = services.add_item(price_list, **serializer.validated_data)
        return Response(PriceListItemSerializer(item).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=PriceListItemUpdateSerializer, responses=PriceListItemSerializer)
    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        item = self.get_object()
        serializer = PriceListItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = services.change_item_price(item, **serializer.validated_data)
        return Response(PriceListItemSerializer(item).data)

    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        services.remove_item(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)
