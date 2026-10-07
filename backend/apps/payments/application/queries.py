"""Leituras públicas de pagamentos para `orders` (sem expor models)."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Count, QuerySet, Sum
from django.db.models.functions import TruncDay, TruncHour

from apps.payments.domain.status import PaymentStatus, RefundStatus
from apps.payments.models import Payment, Refund


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


# Leituras agregadas para o dashboard (faturamento = aprovado - estornado, docs/domain/payments.md)


@dataclass(frozen=True)
class RevenueTotals:
    approved: Decimal  # soma dos pagamentos aprovados (pela data de aprovação)
    refunded: Decimal  # soma dos estornos concluídos (pela data de conclusão)
    approved_count: int

    @property
    def net(self) -> Decimal:
        return self.approved - self.refunded


def _approved(organization_id: UUID, start: datetime, end: datetime) -> QuerySet[Payment]:
    # REFUNDED também foi dinheiro que entrou naquela data; o estorno sai na data dele.
    return Payment.objects.for_organization(organization_id).filter(
        status__in=[PaymentStatus.APPROVED, PaymentStatus.REFUNDED],
        completed_at__gte=start,
        completed_at__lt=end,
    )


def _refunded(organization_id: UUID, start: datetime, end: datetime) -> QuerySet[Refund]:
    return Refund.objects.for_organization(organization_id).filter(
        status=RefundStatus.SUCCEEDED, completed_at__gte=start, completed_at__lt=end
    )


def revenue_totals(organization_id: UUID, start: datetime, end: datetime) -> RevenueTotals:
    approved = _approved(organization_id, start, end).aggregate(total=Sum("amount"), n=Count("id"))
    refunded = _refunded(organization_id, start, end).aggregate(total=Sum("amount"))
    return RevenueTotals(
        approved=approved["total"] or Decimal("0"),
        refunded=refunded["total"] or Decimal("0"),
        approved_count=approved["n"],
    )


def net_revenue_by_bucket(
    organization_id: UUID, start: datetime, end: datetime, bucket: str
) -> dict[datetime, Decimal]:
    """Aprovado - estornado por hora/dia (fuso do negócio) em [start, end)."""
    tz = ZoneInfo(settings.BUSINESS_TIME_ZONE)

    def trunc(field: str) -> TruncDay | TruncHour:
        return TruncHour(field, tzinfo=tz) if bucket == "hour" else TruncDay(field, tzinfo=tz)

    series: dict[datetime, Decimal] = {}
    for row in (
        _approved(organization_id, start, end)
        .annotate(slot=trunc("completed_at"))
        .values("slot")
        .annotate(total=Sum("amount"))
    ):
        series[row["slot"]] = series.get(row["slot"], Decimal("0")) + row["total"]
    for row in (
        _refunded(organization_id, start, end)
        .annotate(slot=trunc("completed_at"))
        .values("slot")
        .annotate(total=Sum("amount"))
    ):
        series[row["slot"]] = series.get(row["slot"], Decimal("0")) - row["total"]
    return series
