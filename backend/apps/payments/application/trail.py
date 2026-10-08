"""Publica a trilha de mudanças de status (auditoria). Sempre na transação da mudança: o evento
nasce com ela no outbox (ADR-011) e nunca sobra nem falta."""

from uuid import UUID

from apps.payments.domain.events import PaymentStatusChanged, RefundStatusChanged
from apps.payments.models import Payment, Refund
from shared.events.bus import publish


def payment_changed(
    payment: Payment, from_status: str | None, actor_id: UUID | None, note: str = ""
) -> None:
    publish(
        PaymentStatusChanged(
            organization_id=payment.organization_id,
            payment_id=payment.id,
            order_id=payment.order_id,
            order_reference=payment.order_reference,
            method=payment.method,
            amount=str(payment.amount),
            from_status=from_status,
            to_status=payment.status,
            actor_id=actor_id,
            note=note,
        )
    )


def refund_changed(
    refund: Refund, from_status: str | None, actor_id: UUID | None, note: str = ""
) -> None:
    payment = refund.payment
    publish(
        RefundStatusChanged(
            organization_id=refund.organization_id,
            refund_id=refund.id,
            payment_id=payment.id,
            order_id=payment.order_id,
            order_reference=payment.order_reference,
            amount=str(refund.amount),
            from_status=from_status,
            to_status=refund.status,
            actor_id=actor_id,
            note=note,
        )
    )
