"""Leituras de pedidos: prévia de preços (a tela não faz contas de dinheiro) e o resumo usado
por outros módulos (notificações) sem expor models."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Count
from django.db.models.functions import TruncDay, TruncHour

from apps.orders.application import resolution
from apps.orders.domain.lines import (
    LineRequest,
    OrderTotals,
    PricedLine,
    compute_totals,
    validate_line_requests,
)
from apps.orders.format import order_reference
from apps.orders.models import Order
from apps.shipping.application.queries import shipment_for_order


@dataclass(frozen=True)
class Quote:
    lines: list[PricedLine]
    totals: OrderTotals


def quote_order(organization_id: UUID, customer_id: UUID, lines: tuple[LineRequest, ...]) -> Quote:
    validate_line_requests(lines, require_lines=False)
    customer = resolution.active_customer(organization_id, customer_id)
    priced = resolution.price_lines(organization_id, customer, lines)
    return Quote(priced, compute_totals(priced))


@dataclass(frozen=True)
class OrderLineView:
    sku: str
    product_name: str
    quantity: int


@dataclass(frozen=True)
class OrderView:
    id: UUID
    reference: str  # "#000003"
    status: str
    customer_id: UUID
    customer_name: str
    total: Decimal
    currency: str
    payment_due_at: datetime | None
    carrier: str
    tracking_code: str
    lines: list[OrderLineView]


def get_order_view(organization_id: UUID, order_id: UUID) -> OrderView | None:
    order = (
        Order.objects.for_organization(organization_id)
        .select_related("customer")
        .prefetch_related("lines")
        .filter(id=order_id)
        .first()
    )
    if order is None:
        return None
    shipment = shipment_for_order(organization_id, order.id)
    return OrderView(
        id=order.id,
        reference=order_reference(order),
        status=order.status,
        customer_id=order.customer_id,
        customer_name=order.customer.display_name,
        total=order.total,
        currency=order.currency,
        payment_due_at=order.payment_due_at,
        carrier=shipment.carrier if shipment else "",
        tracking_code=shipment.tracking_code if shipment else "",
        lines=[
            OrderLineView(line.sku, line.product_name, line.quantity) for line in order.lines.all()
        ],
    )


# Leituras agregadas para o dashboard ------------------------------------------------------------

Bucket = Literal["hour", "day"]

# Pedidos em andamento (o "funil" atual): do envio até a entrega.
OPEN_STATUSES = (
    "PENDING",
    "AWAITING_PAYMENT",
    "PAID",
    "PROCESSING",
    "READY_TO_SHIP",
    "SHIPPED",
)


def _trunc(bucket: Bucket, field: str) -> TruncDay | TruncHour:
    """Dia/hora no fuso do negócio: "hoje" começa à meia-noite de São Paulo, não de UTC."""
    tz = ZoneInfo(settings.BUSINESS_TIME_ZONE)
    return TruncHour(field, tzinfo=tz) if bucket == "hour" else TruncDay(field, tzinfo=tz)


def submitted_orders_by_bucket(
    organization_id: UUID, start: datetime, end: datetime, bucket: Bucket
) -> dict[datetime, int]:
    """Pedidos enviados (`submitted_at`) por hora/dia em [start, end). Rascunhos não contam."""
    rows = (
        Order.objects.for_organization(organization_id)
        .filter(submitted_at__gte=start, submitted_at__lt=end)
        .annotate(slot=_trunc(bucket, "submitted_at"))
        .values("slot")
        .annotate(total=Count("id"))
    )
    return {row["slot"]: row["total"] for row in rows}


def count_submitted_orders(organization_id: UUID, start: datetime, end: datetime) -> int:
    return (
        Order.objects.for_organization(organization_id)
        .filter(submitted_at__gte=start, submitted_at__lt=end)
        .count()
    )


def open_orders_by_status(organization_id: UUID) -> dict[str, int]:
    """Retrato atual do funil (não depende do período): quantos pedidos em cada etapa."""
    rows = (
        Order.objects.for_organization(organization_id)
        .filter(status__in=OPEN_STATUSES)
        .values("status")
        .annotate(total=Count("id"))
    )
    found = {row["status"]: row["total"] for row in rows}
    return {status: found.get(status, 0) for status in OPEN_STATUSES}


@dataclass(frozen=True)
class RecentOrder:
    id: UUID
    reference: str
    customer_name: str
    status: str
    total: Decimal
    submitted_at: datetime


def recent_orders(organization_id: UUID, limit: int = 5) -> list[RecentOrder]:
    orders = (
        Order.objects.for_organization(organization_id)
        .filter(submitted_at__isnull=False)
        .select_related("customer")
        .order_by("-submitted_at")[:limit]
    )
    return [
        RecentOrder(
            order.id,
            order_reference(order),
            order.customer.display_name,
            order.status,
            order.total,
            order.submitted_at,  # type: ignore[arg-type]  # filtrado acima
        )
        for order in orders
    ]
