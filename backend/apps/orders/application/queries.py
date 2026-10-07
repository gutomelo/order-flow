"""Leituras de pedidos: prévia de preços (a tela não faz contas de dinheiro) e o resumo usado
por outros módulos (notificações) sem expor models."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

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
