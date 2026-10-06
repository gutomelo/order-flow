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
