"""Pedido ↔ reserva de estoque (docs/domain/orders.md#implementação-phase-7).

`orders` decide QUANDO reservar e o que fazer com o pedido; `inventory` decide SE há estoque.
"""

from datetime import timedelta
from uuid import UUID

import structlog
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.inventory.application.commands.reservations import (
    ReservationLine,
    ReserveStockCommand,
    release_reservations,
    reserve_stock,
)
from apps.inventory.domain.exceptions import InsufficientStock, StockBusy, WarehouseInactive
from apps.inventory.domain.reservations import ReservationStatus
from apps.orders.application.transitions import transition
from apps.orders.domain.status import OrderStatus
from apps.orders.models import Order

logger = structlog.get_logger(__name__)

# Falhas que deixam o pedido PENDING no envio (a pessoa tenta reservar de novo depois).
DEFERRABLE = (InsufficientStock, StockBusy, WarehouseInactive)


def reserve_order(order: Order, actor_id: UUID | None) -> None:
    """PENDING → AWAITING_PAYMENT reservando todas as linhas (tudo-ou-nada).

    O pedido já está bloqueado pelo chamador (ordem de locks: pedido → estoque).
    """
    if order.warehouse_id is None:  # inalcançável: a submissão exige depósito
        raise ValueError("order without warehouse cannot be reserved")
    expires_at = timezone.now() + timedelta(hours=settings.STOCK_RESERVATION_TTL_HOURS)
    reserve_stock(
        ReserveStockCommand(
            organization_id=order.organization_id,
            actor_id=actor_id,
            warehouse_id=order.warehouse_id,
            order_id=order.id,
            lines=tuple(
                ReservationLine(line.id, line.product_id, line.quantity)
                for line in order.lines.all()
            ),
            expires_at=expires_at,
        )
    )
    order.payment_due_at = expires_at
    transition(order, OrderStatus.AWAITING_PAYMENT, actor_id=actor_id)


def try_reserve_order(order: Order, actor_id: UUID | None) -> bool:
    """No envio: reserva se der; senão o pedido continua PENDING (decisão de produto)."""
    try:
        with transaction.atomic():  # savepoint: uma falha não desfaz o envio
            reserve_order(order, actor_id)
    except DEFERRABLE as exc:
        order.payment_due_at = None
        order.status = OrderStatus.PENDING
        logger.info("orders.reservation.deferred", order_id=str(order.id), code=exc.code)
        return False
    return True


def release_order_stock(order: Order, actor_id: UUID | None, *, expired: bool) -> None:
    release_reservations(
        order.organization_id,
        actor_id,
        order.id,
        reason=ReservationStatus.EXPIRED if expired else ReservationStatus.RELEASED,
    )
    order.payment_due_at = None
