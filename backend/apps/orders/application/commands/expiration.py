"""Jobs periódicos do ciclo de vida (Celery Beat): expiração e pedidos parados.

Rodam para todas as organizações. Cada pedido é tratado na sua própria transação com
`skip_locked`: um pedido sendo pago/cancelado agora é pulado e volta na próxima execução, sem
esperar lock nem travar o lote (docs/architecture/event-driven.md, políticas).
"""

from datetime import datetime, timedelta
from uuid import UUID

import structlog
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.orders.application.reservations import release_order_stock
from apps.orders.application.transitions import transition
from apps.orders.domain.status import OrderStatus
from apps.orders.models import Order
from apps.payments.application.queries import has_payment_in_flight

logger = structlog.get_logger(__name__)

EXPIRED_REASON = "Reserva expirada sem pagamento"
PENDING_TIMEOUT_REASON = "PENDING_TIMEOUT: pendente sem atividade além do prazo"
BATCH_SIZE = 200


def expire_unpaid_order(order_id: UUID, *, now: datetime) -> bool:
    """AWAITING_PAYMENT vencido → PENDING, devolvendo o estoque (reserva EXPIRED)."""
    with transaction.atomic():
        order = (
            Order.objects.select_for_update(skip_locked=True, of=("self",))
            .filter(id=order_id, status=OrderStatus.AWAITING_PAYMENT, payment_due_at__lte=now)
            .first()
        )
        if order is None:  # pago/cancelado/em uso agora: nada a fazer
            return False
        if has_payment_in_flight(order.organization_id, order.id):
            # Cobrança sem resposta ainda: não solta o estoque de quem pode ter pago.
            return False
        release_order_stock(order, None, expired=True)
        transition(order, OrderStatus.PENDING, actor_id=None, reason=EXPIRED_REASON)
    logger.info("orders.order.reservation_expired", order_id=str(order_id))
    return True


def expire_due_orders(now: datetime | None = None) -> int:
    now = now or timezone.now()
    due = (
        Order.objects.filter(status=OrderStatus.AWAITING_PAYMENT, payment_due_at__lte=now)
        .order_by("payment_due_at")
        .values_list("id", flat=True)[:BATCH_SIZE]
    )
    return sum(expire_unpaid_order(order_id, now=now) for order_id in list(due))


def cancel_stale_pending_order(order_id: UUID, *, cutoff: datetime) -> bool:
    with transaction.atomic():
        order = (
            Order.objects.select_for_update(skip_locked=True, of=("self",))
            .filter(id=order_id, status=OrderStatus.PENDING, updated_at__lte=cutoff)
            .first()
        )
        if order is None:
            return False
        transition(order, OrderStatus.CANCELLED, actor_id=None, reason=PENDING_TIMEOUT_REASON)
    logger.info("orders.order.pending_timeout", order_id=str(order_id))
    return True


def cancel_stale_pending_orders(now: datetime | None = None) -> int:
    """PENDING parado há mais de ORDER_PENDING_MAX_AGE_DAYS é cancelado (sem reserva a liberar)."""
    cutoff = (now or timezone.now()) - timedelta(days=settings.ORDER_PENDING_MAX_AGE_DAYS)
    stale = (
        Order.objects.filter(status=OrderStatus.PENDING, updated_at__lte=cutoff)
        .order_by("updated_at")
        .values_list("id", flat=True)[:BATCH_SIZE]
    )
    return sum(cancel_stale_pending_order(order_id, cutoff=cutoff) for order_id in list(stale))
