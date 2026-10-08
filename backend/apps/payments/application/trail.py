"""Publica a trilha de mudanças de status (auditoria). Sempre na transação da mudança: o evento
nasce com ela no outbox (ADR-011) e nunca sobra nem falta."""

from uuid import UUID

from prometheus_client import Counter

from apps.payments.domain.events import PaymentStatusChanged, RefundStatusChanged
from apps.payments.models import Payment, Refund
from shared.events.bus import publish
from shared.observability.metrics import count_after_commit

PAYMENTS = Counter(
    "orderflow_payment_status_changes_total",
    "Mudanças de status de pagamento confirmadas, por forma e status",
    ["method", "status"],
)
REFUNDS = Counter(
    "orderflow_refund_status_changes_total", "Mudanças de status de estorno confirmadas", ["status"]
)


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
    count_after_commit(PAYMENTS, method=payment.method, status=payment.status)


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
    count_after_commit(REFUNDS, status=refund.status)
