"""Leituras públicas de pagamentos para `orders` (sem expor models)."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from apps.payments.domain.status import PaymentStatus
from apps.payments.models import Payment


@dataclass(frozen=True)
class RefundSummary:
    id: UUID
    status: str
    failure_reason: str
    created_at: datetime


@dataclass(frozen=True)
class PaymentSummary:
    id: UUID
    order_id: UUID
    method: str
    status: str
    amount: Decimal
    decline_reason: str
    manual_reference: str
    created_at: datetime
    refunds: list[RefundSummary] = field(default_factory=list)


def _summary(payment: Payment) -> PaymentSummary:
    return PaymentSummary(
        id=payment.id,
        order_id=payment.order_id,
        method=payment.method,
        status=payment.status,
        amount=payment.amount,
        decline_reason=payment.decline_reason,
        manual_reference=payment.manual_reference,
        created_at=payment.created_at,
        refunds=[
            RefundSummary(r.id, r.status, r.failure_reason, r.created_at)
            for r in payment.refunds.all()
        ],
    )


def get_payment(organization_id: UUID, payment_id: UUID) -> PaymentSummary | None:
    payment = Payment.objects.for_organization(organization_id).filter(id=payment_id).first()
    return None if payment is None else _summary(payment)


def payments_for_order(organization_id: UUID, order_id: UUID) -> list[PaymentSummary]:
    payments = (
        Payment.objects.for_organization(organization_id)
        .filter(order_id=order_id)
        .prefetch_related("refunds")
        .order_by("created_at")
    )
    return [_summary(payment) for payment in payments]


def has_payment_in_flight(organization_id: UUID, order_id: UUID) -> bool:
    return (
        Payment.objects.for_organization(organization_id)
        .filter(order_id=order_id, status=PaymentStatus.PENDING)
        .exists()
    )


def approved_payment_id(organization_id: UUID, order_id: UUID) -> UUID | None:
    return (
        Payment.objects.for_organization(organization_id)
        .filter(order_id=order_id, status=PaymentStatus.APPROVED)
        .values_list("id", flat=True)
        .first()
    )
