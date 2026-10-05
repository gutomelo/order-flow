from uuid import UUID

import structlog
from django.db import transaction

from apps.orders.application.transitions import lock_order, transition
from apps.orders.domain.exceptions import CancelReasonRequired, InvalidOrderTransition
from apps.orders.domain.status import OrderStatus
from apps.orders.models import Order

logger = structlog.get_logger(__name__)

# Phase 6: só estados sem reserva nem pagamento. AWAITING_PAYMENT entra com a liberação da reserva
# (Phase 7) e os estados pagos com o refund (Phase 8) — a tabela da máquina já os prevê.
CANCELLABLE_NOW = frozenset({OrderStatus.DRAFT, OrderStatus.PENDING})


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
        transition(order, OrderStatus.CANCELLED, actor_id=actor_id, reason=reason)
    logger.info("orders.order.cancelled", order_id=str(order.id))
    return order
