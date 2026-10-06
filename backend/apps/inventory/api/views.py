from datetime import datetime
from typing import Any, cast
from uuid import UUID

from django.db.models import F, Q, QuerySet
from django.utils.dateparse import parse_datetime
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.domain.permissions import Permission
from apps.identity.models import User
from apps.inventory.api.serializers import (
    AdjustmentCreateSerializer,
    AvailabilityQuerySerializer,
    AvailabilitySerializer,
    ReceiptCreateSerializer,
    ReceiptSerializer,
    StockItemSerializer,
    StockItemUpdateSerializer,
    StockMovementSerializer,
    TransferCreateSerializer,
    WarehouseCreateSerializer,
    WarehouseSerializer,
    WarehouseUpdateSerializer,
)
from apps.inventory.application.commands import warehouses
from apps.inventory.application.commands.adjust_stock import AdjustStock, AdjustStockCommand
from apps.inventory.application.commands.receive_stock import (
    ReceiptLine,
    ReceiveStock,
    ReceiveStockCommand,
)
from apps.inventory.application.commands.transfer_stock import (
    TransferStock,
    TransferStockCommand,
)
from apps.inventory.application.queries import stock_levels
from apps.inventory.models import StockItem, StockMovement, Warehouse
from shared.api.activation import ActivationActionsMixin
from shared.permissions import HasPermission, HasReadWritePermission
from shared.tenancy.api import TenantScopedQuerysetMixin, organization_id_of

INVENTORY_READ_WRITE = HasReadWritePermission(
    read=Permission.INVENTORY_READ, write=Permission.INVENTORY_UPDATE
)


def _uuid_param(request: Request, name: str) -> UUID | None:
    raw = request.query_params.get(name)
    if not raw:
        return None
    try:
        return UUID(raw)
    except ValueError as exc:
        raise ValidationError({name: ["Identificador inválido."]}) from exc


def _datetime_param(request: Request, name: str) -> datetime | None:
    raw = request.query_params.get(name)
    if not raw:
        return None
    value = parse_datetime(raw)
    if value is None or value.tzinfo is None:
        raise ValidationError(
            {name: ["Use data e hora ISO 8601 com fuso (ex.: 2026-10-04T00:00:00Z)."]}
        )
    return value


def _actor_id(request: Request) -> UUID:
    return cast(User, request.user).id


class WarehouseViewSet(
    ActivationActionsMixin,
    TenantScopedQuerysetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet[Warehouse],
):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = (IsAuthenticated, INVENTORY_READ_WRITE)
    http_method_names = ("get", "post", "patch", "head", "options")
    pagination_class = None  # poucos depósitos por organização; usados em seletores
    filterset_fields = ("is_active",)
    ordering = ("code",)

    @extend_schema(request=WarehouseCreateSerializer, responses={201: WarehouseSerializer})
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = WarehouseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        warehouse = warehouses.create_warehouse(self.organization_id, **serializer.validated_data)
        return Response(WarehouseSerializer(warehouse).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=WarehouseUpdateSerializer, responses=WarehouseSerializer)
    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        warehouse = self.get_object()
        serializer = WarehouseUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        warehouses.rename_warehouse(warehouse, name=serializer.validated_data["name"])
        return Response(WarehouseSerializer(warehouse).data)

    def set_active(self, instance: Warehouse, *, is_active: bool) -> Warehouse:
        return warehouses.set_warehouse_active(instance, is_active=is_active)


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter("warehouse", OpenApiTypes.UUID),
            OpenApiParameter("product", OpenApiTypes.UUID),
            OpenApiParameter(
                "low_stock", OpenApiTypes.BOOL, description="available <= ponto de reposição"
            ),
        ]
    )
)
class StockItemViewSet(
    TenantScopedQuerysetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet[StockItem],
):
    queryset = StockItem.objects.select_related("product", "warehouse")
    serializer_class = StockItemSerializer
    permission_classes = (IsAuthenticated, INVENTORY_READ_WRITE)
    http_method_names = ("get", "patch", "head", "options")
    search_fields = ("product__sku", "product__name")
    ordering_fields = ("product__name", "available", "on_hand", "updated_at")
    ordering = ("product__name", "warehouse__code")

    def get_queryset(self) -> QuerySet[StockItem]:
        queryset = cast("QuerySet[StockItem]", super().get_queryset())
        if warehouse := _uuid_param(self.request, "warehouse"):
            queryset = queryset.filter(warehouse_id=warehouse)
        if product := _uuid_param(self.request, "product"):
            queryset = queryset.filter(product_id=product)
        if self.request.query_params.get("low_stock") == "true":
            queryset = queryset.filter(reorder_point__gt=0, available__lte=F("reorder_point"))
        return queryset

    @extend_schema(request=StockItemUpdateSerializer, responses=StockItemSerializer)
    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Ponto de reposição é configuração, não saldo: não passa pelo ledger.
        item = self.get_object()
        serializer = StockItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item.reorder_point = serializer.validated_data["reorder_point"]
        item.save(update_fields=["reorder_point", "updated_at"])
        item.refresh_from_db()  # `available` é calculado pelo banco
        return Response(StockItemSerializer(item).data)


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter("warehouse", OpenApiTypes.UUID),
            OpenApiParameter("product", OpenApiTypes.UUID),
            OpenApiParameter("stock_item", OpenApiTypes.UUID),
            OpenApiParameter("reference", OpenApiTypes.UUID),
            OpenApiParameter("created_after", OpenApiTypes.DATETIME),
            OpenApiParameter("created_before", OpenApiTypes.DATETIME),
        ]
    )
)
class StockMovementViewSet(
    TenantScopedQuerysetMixin, mixins.ListModelMixin, viewsets.GenericViewSet[StockMovement]
):
    """Histórico imutável de movimentações (mais recentes primeiro)."""

    queryset = StockMovement.objects.select_related(
        "stock_item__product", "stock_item__warehouse", "performed_by"
    )
    serializer_class = StockMovementSerializer
    permission_classes = (IsAuthenticated, HasPermission(Permission.INVENTORY_READ))
    filterset_fields = ("type",)
    search_fields = ("stock_item__product__sku", "stock_item__product__name", "reason")
    ordering = ("-created_at",)

    def get_queryset(self) -> QuerySet[StockMovement]:
        queryset = cast("QuerySet[StockMovement]", super().get_queryset())
        filters = Q()
        if warehouse := _uuid_param(self.request, "warehouse"):
            filters &= Q(stock_item__warehouse_id=warehouse)
        if product := _uuid_param(self.request, "product"):
            filters &= Q(stock_item__product_id=product)
        if stock_item := _uuid_param(self.request, "stock_item"):
            filters &= Q(stock_item_id=stock_item)
        if reference := _uuid_param(self.request, "reference"):
            filters &= Q(reference_id=reference)
        if after := _datetime_param(self.request, "created_after"):
            filters &= Q(created_at__gte=after)
        if before := _datetime_param(self.request, "created_before"):
            filters &= Q(created_at__lt=before)
        return queryset.filter(filters)


class ReceiptView(APIView):
    permission_classes = (IsAuthenticated, HasPermission(Permission.INVENTORY_UPDATE))

    @extend_schema(request=ReceiptCreateSerializer, responses={201: ReceiptSerializer})
    def post(self, request: Request) -> Response:
        serializer = ReceiptCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = ReceiveStock().execute(
            ReceiveStockCommand(
                organization_id=organization_id_of(request),
                actor_id=_actor_id(request),
                warehouse_id=data["warehouse_id"],
                supplier_id=data["supplier_id"],
                document_number=data["document_number"],
                notes=data["notes"],
                lines=tuple(ReceiptLine(**line) for line in data["lines"]),
            )
        )
        movements = list(
            StockMovement.objects.select_related(
                "stock_item__product", "stock_item__warehouse", "performed_by"
            ).filter(id__in=[m.id for m in result.movements])
        )
        body = ReceiptSerializer(result.receipt, context={"movements": movements}).data
        return Response(body, status=status.HTTP_201_CREATED)


class AdjustmentView(APIView):
    permission_classes = (IsAuthenticated, HasPermission(Permission.INVENTORY_ADJUST))

    @extend_schema(request=AdjustmentCreateSerializer, responses=StockItemSerializer)
    def post(self, request: Request) -> Response:
        serializer = AdjustmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AdjustStock().execute(
            AdjustStockCommand(
                organization_id=organization_id_of(request),
                actor_id=_actor_id(request),
                **serializer.validated_data,
            )
        )
        item = StockItem.objects.select_related("product", "warehouse").get(id=result.stock_item.id)
        return Response(StockItemSerializer(item).data)


class TransferView(APIView):
    permission_classes = (IsAuthenticated, HasPermission(Permission.INVENTORY_UPDATE))

    @extend_schema(
        request=TransferCreateSerializer, responses={201: StockItemSerializer(many=True)}
    )
    def post(self, request: Request) -> Response:
        serializer = TransferCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = TransferStock().execute(
            TransferStockCommand(
                organization_id=organization_id_of(request),
                actor_id=_actor_id(request),
                **serializer.validated_data,
            )
        )
        items = StockItem.objects.select_related("product", "warehouse").filter(
            id__in=[result.source.id, result.destination.id]
        )
        by_id = {item.id: item for item in items}
        body = {
            "transfer_id": str(result.transfer_id),
            "source": StockItemSerializer(by_id[result.source.id]).data,
            "destination": StockItemSerializer(by_id[result.destination.id]).data,
        }
        return Response(body, status=status.HTTP_201_CREATED)


class AvailabilityView(APIView):
    """Disponível por produto num depósito — informação para a tela de pedido.

    Leitura sem lock: o número pode mudar até a reserva, que é quem decide (ADR-008).
    """

    permission_classes = (IsAuthenticated, HasPermission(Permission.INVENTORY_READ))

    @extend_schema(
        parameters=[
            OpenApiParameter("warehouse", OpenApiTypes.UUID, required=True),
            OpenApiParameter(
                "products",
                OpenApiTypes.UUID,
                required=True,
                many=True,
                explode=False,
                description="IDs separados por vírgula (até 200).",
            ),
        ],
        responses=AvailabilitySerializer(many=True),
    )
    def get(self, request: Request) -> Response:
        raw = request.query_params.get("products", "")
        query = AvailabilityQuerySerializer(
            data={
                "warehouse": request.query_params.get("warehouse"),
                "products": [p for p in raw.split(",") if p],
            }
        )
        query.is_valid(raise_exception=True)
        levels = stock_levels(
            organization_id_of(request),
            query.validated_data["warehouse"],
            query.validated_data["products"],
        )
        body = [
            {
                "product_id": pid,
                "on_hand": lv.on_hand,
                "reserved": lv.reserved,
                "available": lv.available,
            }
            for pid, lv in levels.items()
        ]
        # `many=True` recebe a lista; os stubs tipam a instância como um único item.
        return Response(AvailabilitySerializer(cast(Any, body), many=True).data)
