from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

import structlog
from django.db import transaction
from django.utils import timezone

from apps.orders.application import resolution
from apps.orders.application.persistence import apply_lines, next_order_number
from apps.orders.application.reservations import try_reserve_order
from apps.orders.application.transitions import lock_order, transition
from apps.orders.domain.exceptions import AddressRequired
from apps.orders.domain.lines import (
    LineRequest,
    compute_totals,
    ensure_expected_total,
    validate_line_requests,
)
from apps.orders.domain.state_machine import assert_transition
from apps.orders.domain.status import OrderStatus
from apps.orders.models import Order

logger = structlog.get_logger(__name__)


def _finalize(
    order: Order,
    lines: tuple[LineRequest, ...],
    *,
    shipping_address_id: UUID | None,
    expected_total: Decimal | None,
    actor_id: UUID,
) -> None:
    """Revalida tudo, recota, confere o total esperado, congela, numera e copia o endereço."""
    organization_id = order.organization_id
    validate_line_requests(lines, require_lines=True)  # O1
    customer = resolution.active_customer(organization_id, order.customer_id)
    warehouse = resolution.chosen_warehouse(organization_id, order.warehouse_id, required=True)
    address = resolution.chosen_address(
        organization_id, customer.id, shipping_address_id, required=True
    )
    if address is None:  # inalcançável com required=True; mantém o tipo explícito
        raise AddressRequired(details={"field": "shipping_address_id"})
    priced = resolution.price_lines(organization_id, customer, lines)
    ensure_expected_total(expected_total, compute_totals(priced).total)
    order.warehouse = warehouse
    order.shipping_address = address
    order.shipping_snapshot = resolution.address_snapshot(address)
    order.number = next_order_number(organization_id)
    order.submitted_at = timezone.now()
    # A transição grava o pedido (novo ou rascunho) e o histórico; depois as linhas congeladas
    # substituem as do rascunho e os totais são persistidos.
    transition(order, OrderStatus.PENDING, actor_id=actor_id)
    apply_lines(order, priced)
    order.save()
    # Com estoque, segue para AWAITING_PAYMENT; sem estoque, fica PENDING (decisão de produto).
    try_reserve_order(order, actor_id)


def submit_order(
    organization_id: UUID, actor_id: UUID, order_id: UUID, *, expected_total: Decimal | None
) -> Order:
    """DRAFT → PENDING (→ AWAITING_PAYMENT se houver estoque).

    Idempotente por estado: reenviar um pedido já enviado (PENDING ou AWAITING_PAYMENT) não tem
    efeito.
    """
    with transaction.atomic():
        order = lock_order(organization_id, order_id)
        if order.status in (OrderStatus.PENDING, OrderStatus.AWAITING_PAYMENT):
            return order
        # Falha cedo (ex.: pedido cancelado) antes de recotar e reservar um número.
        assert_transition(OrderStatus(order.status), OrderStatus.PENDING)
        lines = tuple(LineRequest(line.product_id, line.quantity) for line in order.lines.all())
        _finalize(
            order,
            lines,
            shipping_address_id=order.shipping_address_id,
            expected_total=expected_total,
            actor_id=actor_id,
        )
    logger.info("orders.order.submitted", order_id=str(order.id), number=order.number)
    return order


@dataclass(frozen=True)
class PlaceOrderInput:
    customer_id: UUID
    warehouse_id: UUID | None
    lines: tuple[LineRequest, ...]
    shipping_address_id: UUID | None = None
    purchase_order_number: str = ""
    notes: str = ""
    expected_total: Decimal | None = field(default=None)


def place_order(organization_id: UUID, actor_id: UUID, data: PlaceOrderInput) -> Order:
    """— → PENDING numa chamada (a view exige Idempotency-Key, ADR-012)."""
    with transaction.atomic():
        customer = resolution.active_customer(organization_id, data.customer_id)
        order = Order(
            organization_id=organization_id,
            customer=customer,
            warehouse_id=data.warehouse_id,
            purchase_order_number=data.purchase_order_number.strip(),
            notes=data.notes.strip(),
            created_by_id=actor_id,
        )
        _finalize(
            order,
            data.lines,
            shipping_address_id=data.shipping_address_id,
            expected_total=data.expected_total,
            actor_id=actor_id,
        )
    logger.info("orders.order.placed", order_id=str(order.id), number=order.number)
    return order
