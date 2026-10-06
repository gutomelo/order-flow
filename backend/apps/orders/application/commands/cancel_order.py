from uuid import UUID

import structlog
from django.db import transaction

from apps.orders.application.reservations import release_order_stock
from apps.orders.application.transitions import lock_order, transition
from apps.orders.domain.exceptions import CancelReasonRequired, InvalidOrderTransition
from apps.orders.domain.status import OrderStatus
from apps.orders.models import Order

logger = structlog.get_logger(__name__)

# Estados pagos (PAID, PROCESSING, READY_TO_SHIP) entram com o refund na Phase 8 — a tabela da
# máquina já os prevê.
CANCELLABLE_NOW = frozenset({OrderStatus.DRAFT, OrderStatus.PENDING, OrderStatus.AWAITING_PAYMENT})


def cancel_order(organization_id: UUID, actor_id: UUID, order_id: UUID, *, reason: str) -> Order:
    reason = reason.strip()
    if not reason:
        raise CancelReasonRequired(details={"field": "reason"})
    with transaction.atomic():
        order = lock_order(organization_id, order_id)
        if order.status == OrderStatus.CANCELLED:  # idempotente por estado
            return order
        if order.status not in CANCELLABLE_NOW:
            raise InvalidOrderTransition(
                details={"from": order.status, "to": OrderStatus.CANCELLED.value}
            )
        if order.status == OrderStatus.AWAITING_PAYMENT:
            # Mesma transação: o pedido cancelado nunca fica segurando estoque.
            release_order_stock(order, actor_id, expired=False)
        transition(order, OrderStatus.CANCELLED, actor_id=actor_id, reason=reason)
    logger.info("orders.order.cancelled", order_id=str(order.id))
    return order
