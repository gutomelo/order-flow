from uuid import UUID

import structlog
from django.db import transaction

from apps.orders.application.reservations import release_order_stock
from apps.orders.application.transitions import lock_order, transition
from apps.orders.domain.exceptions import CancelReasonRequired, InvalidOrderTransition
from apps.orders.domain.state_machine import CANCEL_REQUIRES_REFUND
from apps.orders.domain.status import OrderStatus
from apps.orders.models import Order
from apps.payments.application.queries import approved_payment_id
from apps.payments.application.refunds import request_refund

logger = structlog.get_logger(__name__)

# Estados pagos exigem `orders:cancel_paid` (domain/policies.py) e geram estorno.
CANCELLABLE_NOW = (
    frozenset({OrderStatus.DRAFT, OrderStatus.PENDING, OrderStatus.AWAITING_PAYMENT})
    | CANCEL_REQUIRES_REFUND
)
HOLDS_STOCK = frozenset({OrderStatus.AWAITING_PAYMENT}) | CANCEL_REQUIRES_REFUND


def cancel_order(organization_id: UUID, actor_id: UUID, order_id: UUID, *, reason: str) -> Order:
    reason = reason.strip()
    if not reason:
        raise CancelReasonRequired(details={"field": "reason"})
    with transaction.atomic():
        order = lock_order(organization_id, order_id)
        if order.status == OrderStatus.CANCELLED:  # idempotente por estado
            return order
        previous = OrderStatus(order.status)
        if previous not in CANCELLABLE_NOW:
            raise InvalidOrderTransition(
                details={"from": order.status, "to": OrderStatus.CANCELLED.value}
            )
        if previous in HOLDS_STOCK:
            # Mesma transação: o pedido cancelado nunca fica segurando estoque.
            release_order_stock(order, actor_id, expired=False)
        transition(order, OrderStatus.CANCELLED, actor_id=actor_id, reason=reason)
        if previous in CANCEL_REQUIRES_REFUND:
            payment_id = approved_payment_id(organization_id, order.id)
            if payment_id is not None:  # o estorno sai pelo outbox: nada se perde após o commit
                request_refund(organization_id, actor_id, payment_id, reason=reason)
    logger.info("orders.order.cancelled", order_id=str(order.id), previous=previous.value)
    return order
