"""Pagamento do pedido (docs/domain/orders.md#fluxo-de-pagamento-payorder).

    Tx 1      bloqueia o pedido, exige AWAITING_PAYMENT, cria o pagamento PENDING
    (fora)    chama o gateway — nada de I/O externo segurando lock de pedido ou estoque
    Tx 2      aplica o resultado (`apply_payment_result`, idempotente)

`apply_payment_result` também é chamado pelo handler de `payments.payment.approved` (aprovação
vinda da reconciliação ou da baixa manual): quem chegar primeiro aplica, o outro não faz nada.
"""

from uuid import UUID

import structlog
from django.db import transaction

from apps.inventory.application.commands.reservations import confirm_reservations
from apps.orders.application.reservations import try_reserve_order
from apps.orders.application.transitions import lock_order, transition
from apps.orders.domain.exceptions import OrderNotAwaitingPayment
from apps.orders.domain.status import OrderStatus
from apps.orders.format import order_reference
from apps.orders.models import Order
from apps.payments.application import charges, refunds
from apps.payments.application.queries import get_payment
from apps.payments.domain.exceptions import PaymentDeclined
from apps.payments.domain.status import PaymentStatus

logger = structlog.get_logger(__name__)

PAID_REASON = "Pagamento aprovado"
NO_STOCK_REFUND_REASON = "Aprovado após a reserva expirar e sem estoque para reservar de novo"
CANCELLED_REFUND_REASON = "Pagamento aprovado depois do cancelamento do pedido"


def pay_order(
    organization_id: UUID, actor_id: UUID, order_id: UUID, *, card_token: str
) -> tuple[Order, str]:
    """Cobra o total do pedido. Devolve o pedido e o status do pagamento (PENDING ⇒ 202)."""
    with transaction.atomic():
        order = lock_order(organization_id, order_id)
        if order.status != OrderStatus.AWAITING_PAYMENT:
            raise OrderNotAwaitingPayment(details={"status": order.status})
        payment = charges.create_pending_card_payment(
            organization_id,
            actor_id,
            order_id=order.id,
            order_reference=order_reference(order),
            amount=order.total,
        )
    payment = charges.execute_charge(payment.id, card_token)
    if payment.status == PaymentStatus.DECLINED:
        raise PaymentDeclined(
            details={"reason": payment.decline_reason, "payment_id": str(payment.id)}
        )
    if payment.status == PaymentStatus.APPROVED:
        return apply_payment_result(organization_id, order.id, payment.id, actor_id), payment.status
    return Order.objects.get(id=order.id), payment.status


def record_manual_payment(
    organization_id: UUID, actor_id: UUID, order_id: UUID, *, reference: str
) -> Order:
    """Baixa do financeiro: pagamento e pedido mudam na mesma transação."""
    with transaction.atomic():
        order = lock_order(organization_id, order_id)
        if order.status != OrderStatus.AWAITING_PAYMENT:
            raise OrderNotAwaitingPayment(details={"status": order.status})
        charges.record_manual_payment(
            organization_id,
            actor_id,
            order_id=order.id,
            order_reference=order_reference(order),
            amount=order.total,
            reference=reference,
        )
        _mark_paid(order, actor_id)
    return order


def apply_payment_result(
    organization_id: UUID, order_id: UUID, payment_id: UUID, actor_id: UUID | None = None
) -> Order:
    """Leva o pedido ao estado coerente com um pagamento aprovado. Idempotente."""
    with transaction.atomic():
        order = lock_order(organization_id, order_id)
        payment = get_payment(organization_id, payment_id)
        if payment is None or payment.status != PaymentStatus.APPROVED:
            return order
        if order.status == OrderStatus.PAID:
            return order
        if order.status == OrderStatus.PENDING and not try_reserve_order(order, actor_id):
            # A reserva expirou durante a cobrança e o estoque acabou: devolve o dinheiro.
            refunds.request_refund(organization_id, None, payment_id, reason=NO_STOCK_REFUND_REASON)
            logger.warning("orders.payment.refunded_no_stock", order_id=str(order.id))
            return order
        if order.status == OrderStatus.AWAITING_PAYMENT:
            _mark_paid(order, actor_id)
            return order
        # Cancelado (ou outro estado que não aceita pagamento): o dinheiro volta.
        refunds.request_refund(organization_id, None, payment_id, reason=CANCELLED_REFUND_REASON)
        logger.warning("orders.payment.refunded_late", order_id=str(order.id), status=order.status)
    return order


def _mark_paid(order: Order, actor_id: UUID | None) -> None:
    confirm_reservations(order.organization_id, order.id)  # reserva não expira mais
    order.payment_due_at = None
    transition(order, OrderStatus.PAID, actor_id=actor_id, reason=PAID_REASON)
    logger.info("orders.order.paid", order_id=str(order.id))


def mark_order_refunded(organization_id: UUID, order_id: UUID) -> Order:
    """`PaymentRefunded`: pedido cancelado e pago → REFUNDED. Outros estados não mudam
    (ex.: aprovado sem estoque segue PENDING; o estorno só devolveu o dinheiro)."""
    with transaction.atomic():
        order = lock_order(organization_id, order_id)
        if order.status == OrderStatus.CANCELLED:
            transition(order, OrderStatus.REFUNDED, actor_id=None, reason="Estorno concluído")
    return order
