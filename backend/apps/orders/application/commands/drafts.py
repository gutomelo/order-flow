from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import structlog
from django.db import transaction

from apps.orders.application import resolution
from apps.orders.application.persistence import apply_lines
from apps.orders.application.transitions import lock_order, transition
from apps.orders.domain.exceptions import OrderNotEditable
from apps.orders.domain.lines import LineRequest, validate_line_requests
from apps.orders.domain.status import OrderStatus
from apps.orders.models import Order

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class DraftInput:
    customer_id: UUID
    warehouse_id: UUID | None = None
    shipping_address_id: UUID | None = None
    purchase_order_number: str = ""
    notes: str = ""
    lines: tuple[LineRequest, ...] = field(default_factory=tuple)


def save_draft(organization_id: UUID, actor_id: UUID, data: DraftInput) -> Order:
    """— → DRAFT. Linhas, depósito e endereço podem ficar para depois; preços são estimativa."""
    validate_line_requests(data.lines, require_lines=False)
    with transaction.atomic():
        customer = resolution.active_customer(organization_id, data.customer_id)
        warehouse = resolution.chosen_warehouse(organization_id, data.warehouse_id, required=False)
        address = resolution.chosen_address(
            organization_id, customer.id, data.shipping_address_id, required=False
        )
        lines = resolution.price_lines(organization_id, customer, data.lines)
        order = Order(
            organization_id=organization_id,
            customer=customer,
            warehouse=warehouse,
            shipping_address=address,
            purchase_order_number=data.purchase_order_number.strip(),
            notes=data.notes.strip(),
            created_by_id=actor_id,
        )
        transition(order, OrderStatus.DRAFT, actor_id=actor_id)
        apply_lines(order, lines)
        order.save()
    logger.info("orders.draft.created", order_id=str(order.id))
    return order


def update_draft(
    organization_id: UUID, actor_id: UUID, order_id: UUID, changes: Mapping[str, Any]
) -> Order:
    """Edição de rascunho (O6: só rascunhos). Recota todas as linhas: o preço pode ter mudado."""
    lines: tuple[LineRequest, ...] | None = changes.get("lines")
    if lines is not None:
        validate_line_requests(lines, require_lines=False)
    with transaction.atomic():
        order = lock_order(organization_id, order_id)
        if order.status != OrderStatus.DRAFT:
            raise OrderNotEditable()
        customer_id = changes.get("customer_id", order.customer_id)
        customer = resolution.active_customer(organization_id, customer_id)
        customer_changed = customer.id != order.customer_id
        order.customer = customer
        if "warehouse_id" in changes:
            order.warehouse = resolution.chosen_warehouse(
                organization_id, changes["warehouse_id"], required=False
            )
        if "shipping_address_id" in changes or customer_changed:
            # Trocar o cliente invalida o endereço escolhido: volta para a entrega padrão dele.
            address_id = changes.get("shipping_address_id") if not customer_changed else None
            order.shipping_address = resolution.chosen_address(
                organization_id, customer.id, address_id, required=False
            )
        for name in ("purchase_order_number", "notes"):
            if name in changes:
                setattr(order, name, changes[name].strip())
        if lines is None:
            lines = tuple(LineRequest(line.product_id, line.quantity) for line in order.lines.all())
        apply_lines(order, resolution.price_lines(organization_id, customer, lines))
        order.save()
    return order
