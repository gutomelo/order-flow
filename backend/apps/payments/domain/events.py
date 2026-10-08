from dataclasses import dataclass
from uuid import UUID

from shared.events.base import DomainEvent


@dataclass(frozen=True, kw_only=True)
class PaymentApproved(DomainEvent):
    event_name = "payments.payment.approved"

    organization_id: UUID
    payment_id: UUID
    order_id: UUID


@dataclass(frozen=True, kw_only=True)
class RefundRequested(DomainEvent):
    event_name = "payments.refund.requested"

    organization_id: UUID
    refund_id: UUID


@dataclass(frozen=True, kw_only=True)
class PaymentRefunded(DomainEvent):
    event_name = "payments.payment.refunded"

    organization_id: UUID
    payment_id: UUID
    refund_id: UUID
    order_id: UUID


@dataclass(frozen=True, kw_only=True)
class PaymentStatusChanged(DomainEvent):
    """Toda mudança de status de pagamento (inclusive a criação). Para trilha de auditoria: leva
    valor, forma e quem fez (`None` = sistema: reconciliação, provedor)."""

    event_name = "payments.payment.status_changed"

    organization_id: UUID
    payment_id: UUID
    order_id: UUID
    order_reference: str
    method: str
    amount: str
    from_status: str | None
    to_status: str
    actor_id: UUID | None
    note: str  # motivo da recusa, referência da baixa manual...


@dataclass(frozen=True, kw_only=True)
class RefundStatusChanged(DomainEvent):
    event_name = "payments.refund.status_changed"

    organization_id: UUID
    refund_id: UUID
    payment_id: UUID
    order_id: UUID
    order_reference: str
    amount: str
    from_status: str | None
    to_status: str
    actor_id: UUID | None
    note: str  # motivo do estorno ou da falha
