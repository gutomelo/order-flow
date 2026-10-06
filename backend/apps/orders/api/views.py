from collections.abc import Sequence
from typing import TYPE_CHECKING, Any
from uuid import UUID

from django.db.models import Count, QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from apps.identity.domain.permissions import Permission
from apps.orders.api.serializers import (
    CancelSerializer,
    DraftSerializer,
    OrderSerializer,
    OrderSummarySerializer,
    PlaceOrderSerializer,
    QuoteRequestSerializer,
    QuoteSerializer,
    SubmitSerializer,
)
from apps.orders.application.commands import (
    cancel_order,
    drafts,
    reserve_order_stock,
    submission,
)
from apps.orders.application.queries import quote_order
from apps.orders.domain.lines import LineRequest
from apps.orders.models import Order
from shared.idempotency.decorators import HEADER, idempotent
from shared.permissions import HasPermission
from shared.tenancy.api import TenantScopedQuerysetMixin

if TYPE_CHECKING:
    from rest_framework.permissions import _SupportsHasPermission

# Permissão por ação (security.md, matriz): ler, criar/editar/enviar, cancelar.
_ACTION_PERMISSIONS: dict[str, Permission] = {
    "create": Permission.ORDERS_CREATE,
    "drafts": Permission.ORDERS_CREATE,
    "partial_update": Permission.ORDERS_CREATE,
    "submit": Permission.ORDERS_CREATE,
    "quote": Permission.ORDERS_CREATE,
    "reserve": Permission.ORDERS_CREATE,
    "cancel": Permission.ORDERS_CANCEL,
}

_IDEMPOTENCY_HEADER = OpenApiParameter(
    HEADER,
    OpenApiTypes.UUID,
    OpenApiParameter.HEADER,
    required=True,
    description="UUID gerado pelo cliente por intenção; repetir a chave devolve a mesma resposta.",
)


def _lines(raw: Sequence[dict[str, Any]]) -> tuple[LineRequest, ...]:
    return tuple(LineRequest(item["product_id"], item["quantity"]) for item in raw)


class OrderViewSet(
    TenantScopedQuerysetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet[Order],
):
    queryset = Order.objects.select_related(
        "customer", "warehouse", "created_by", "shipping_address"
    ).annotate(lines_count=Count("lines"))
    permission_classes = (IsAuthenticated,)
    http_method_names = ("get", "post", "patch", "head", "options")
    filterset_fields = ("status", "customer")
    search_fields = (
        "number",
        "customer__legal_name",
        "customer__trade_name",
        "purchase_order_number",
    )
    ordering_fields = ("created_at", "submitted_at", "number", "total")
    ordering = ("-created_at",)

    def get_permissions(self) -> Sequence["_SupportsHasPermission"]:
        required = _ACTION_PERMISSIONS.get(self.action or "", Permission.ORDERS_READ)
        return [IsAuthenticated(), HasPermission(required)()]

    def get_serializer_class(self) -> type[BaseSerializer[Order]]:
        return OrderSummarySerializer if self.action == "list" else OrderSerializer

    def get_queryset(self) -> QuerySet[Order]:
        queryset = super().get_queryset()
        if self.action != "list":
            queryset = queryset.prefetch_related("lines", "history__changed_by")
        return queryset

    @property
    def actor_id(self) -> UUID:
        user: Any = self.request.user
        return UUID(str(user.id))

    def _respond(self, order: Order, status_code: int = status.HTTP_200_OK) -> Response:
        fresh = self.get_queryset().get(id=order.id)
        return Response(OrderSerializer(fresh).data, status=status_code)

    @extend_schema(
        request=PlaceOrderSerializer,
        responses={201: OrderSerializer},
        parameters=[_IDEMPOTENCY_HEADER],
    )
    @idempotent("orders.place")
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = PlaceOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        order = submission.place_order(
            self.organization_id,
            self.actor_id,
            submission.PlaceOrderInput(lines=_lines(data.pop("lines")), **data),
        )
        return self._respond(order, status.HTTP_201_CREATED)

    @extend_schema(request=DraftSerializer, responses={201: OrderSerializer})
    @action(detail=False, methods=["post"])
    def drafts(self, request: Request) -> Response:
        serializer = DraftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        order = drafts.save_draft(
            self.organization_id,
            self.actor_id,
            drafts.DraftInput(lines=_lines(data.pop("lines", [])), **data),
        )
        return self._respond(order, status.HTTP_201_CREATED)

    @extend_schema(request=DraftSerializer, responses=OrderSerializer)
    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        order = self.get_object()
        serializer = DraftSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changes = dict(serializer.validated_data)
        if "lines" in changes:
            changes["lines"] = _lines(changes["lines"])
        order = drafts.update_draft(self.organization_id, self.actor_id, order.id, changes)
        return self._respond(order)

    @extend_schema(request=SubmitSerializer, responses=OrderSerializer)
    @action(detail=True, methods=["post"])
    def submit(self, request: Request, pk: str | None = None) -> Response:
        order = self.get_object()
        serializer = SubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = submission.submit_order(
            self.organization_id,
            self.actor_id,
            order.id,
            expected_total=serializer.validated_data.get("expected_total"),
        )
        return self._respond(order)

    @extend_schema(request=None, responses=OrderSerializer)
    @action(detail=True, methods=["post"])
    def reserve(self, request: Request, pk: str | None = None) -> Response:
        order = self.get_object()
        order = reserve_order_stock.reserve_order_stock(
            self.organization_id, self.actor_id, order.id
        )
        return self._respond(order)

    @extend_schema(request=CancelSerializer, responses=OrderSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        order = self.get_object()
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = cancel_order.cancel_order(
            self.organization_id, self.actor_id, order.id, **serializer.validated_data
        )
        return self._respond(order)

    @extend_schema(request=QuoteRequestSerializer, responses=QuoteSerializer)
    @action(detail=False, methods=["post"])
    def quote(self, request: Request) -> Response:
        serializer = QuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quote = quote_order(
            self.organization_id,
            serializer.validated_data["customer_id"],
            _lines(serializer.validated_data["lines"]),
        )
        return Response(QuoteSerializer(QuoteSerializer.from_quote(quote)).data)
