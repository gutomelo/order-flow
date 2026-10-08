from uuid import UUID

import structlog
from django.db import transaction

from apps.orders.application.reservations import reserve_order
from apps.orders.application.transitions import lock_order
from apps.orders.domain.state_machine import assert_transition
from apps.orders.domain.status import OrderStatus
from apps.orders.models import Order

logger = structlog.get_logger(__name__)


def reserve_order_stock(organization_id: UUID, actor_id: UUID, order_id: UUID) -> Order:
    """Nova tentativa de reserva de um pedido PENDING (após falta ou expiração).

    Ação explícita: falta de estoque é erro (`INSUFFICIENT_STOCK` com cada item), não adiamento.
    Idempotente por estado: pedido já AWAITING_PAYMENT volta sem efeito.
    """
    with transaction.atomic():
        order = lock_order(organization_id, order_id)
        if order.status == OrderStatus.AWAITING_PAYMENT:
            return order
        assert_transition(OrderStatus(order.status), OrderStatus.AWAITING_PAYMENT)
        reserve_order(order, actor_id)
    logger.info("orders.order.reserved", order_id=str(order.id))
    return order
