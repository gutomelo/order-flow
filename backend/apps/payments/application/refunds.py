"""Estornos totais (P5). Pedidos pelo `orders`; executados por handler do outbox (I/O no gateway
fora da transação de quem pediu); concluídos publicam `PaymentRefunded`."""

from uuid import UUID

import structlog
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.payments.domain.events import PaymentRefunded, RefundRequested
from apps.payments.domain.exceptions import RefundNotManual, RefundNotRetryable
from apps.payments.domain.policies import assert_payment_transition, assert_refund_transition
from apps.payments.domain.status import PaymentMethod, PaymentStatus, RefundStatus
from apps.payments.infrastructure.gateways import get_payment_gateway
from apps.payments.models import Payment, Refund
from shared.events.bus import publish

logger = structlog.get_logger(__name__)


def request_refund(
    organization_id: UUID, actor_id: UUID | None, payment_id: UUID, *, reason: str
) -> Refund:
    """Cria o estorno PENDING e publica `RefundRequested` na transação de quem chama.

    Idempotente: se já há estorno vivo ou concluído para o pagamento, devolve esse.
    """
    payment = (
        Payment.objects.for_organization(organization_id).select_for_update().get(id=payment_id)
    )
    existing = payment.refunds.filter(
        status__in=[RefundStatus.PENDING, RefundStatus.SUCCEEDED]
    ).first()
    if existing is not None:
        return existing
    assert_payment_transition(PaymentStatus(payment.status), PaymentStatus.REFUNDED)
    try:
        with transaction.atomic():
            refund = Refund.objects.create(
                organization_id=organization_id,
                payment=payment,
                amount=payment.amount,
                status=RefundStatus.PENDING,
                reason=reason,
                requested_by_id=actor_id,
            )
    except IntegrityError:  # P5: outra transação criou o estorno ao mesmo tempo
        return payment.refunds.get(status__in=[RefundStatus.PENDING, RefundStatus.SUCCEEDED])
    publish(RefundRequested(organization_id=organization_id, refund_id=refund.id))
    logger.info("payments.refund.requested", refund_id=str(refund.id))
    return refund


def process_refund(refund_id: UUID) -> Refund:
    """Executa um estorno de cartão no gateway. Falha transitória sobe (a task tenta de novo)."""
    refund = Refund.objects.select_for_update().select_related("payment").get(id=refund_id)
    if refund.status != RefundStatus.PENDING or refund.payment.method == PaymentMethod.MANUAL:
        return refund  # já resolvido, ou estorno manual (aguarda confirmação do financeiro)
    result = get_payment_gateway().refund(
        idempotency_key=refund.idempotency_key,
        provider_reference=refund.payment.provider_reference,
        amount=refund.amount,
    )
    refund.attempts += 1
    refund.provider_reference = result.provider_reference
    if result.status == "SUCCEEDED":
        _complete(refund)
    else:
        assert_refund_transition(RefundStatus.PENDING, RefundStatus.FAILED)
        refund.status = RefundStatus.FAILED
        refund.failure_reason = result.failure_reason
        refund.save()
        logger.warning("payments.refund.failed", refund_id=str(refund.id))
    return refund


def _complete(refund: Refund) -> None:
    assert_refund_transition(RefundStatus(refund.status), RefundStatus.SUCCEEDED)
    refund.status = RefundStatus.SUCCEEDED
    refund.failure_reason = ""
    refund.completed_at = timezone.now()
    refund.save()
    payment = refund.payment
    assert_payment_transition(PaymentStatus(payment.status), PaymentStatus.REFUNDED)
    payment.status = PaymentStatus.REFUNDED
    payment.save(update_fields=["status", "updated_at"])
    publish(
        PaymentRefunded(
            organization_id=refund.organization_id,
            payment_id=payment.id,
            refund_id=refund.id,
            order_id=payment.order_id,
        )
    )
    logger.info("payments.refund.succeeded", refund_id=str(refund.id))


def retry_refund(organization_id: UUID, actor_id: UUID, refund_id: UUID) -> Refund:
    with transaction.atomic():
        refund = (
            Refund.objects.for_organization(organization_id)
            .select_for_update()
            .select_related("payment")
            .get(id=refund_id)
        )
        if refund.status != RefundStatus.FAILED or refund.payment.method != PaymentMethod.CARD:
            raise RefundNotRetryable()
        refund.status = RefundStatus.PENDING
        refund.failure_reason = ""  # o motivo era da tentativa anterior
        refund.requested_by_id = actor_id
        refund.save()
        publish(RefundRequested(organization_id=organization_id, refund_id=refund.id))
    return refund


def confirm_manual_refund(organization_id: UUID, actor_id: UUID, refund_id: UUID) -> Refund:
    """O financeiro devolveu o dinheiro fora do sistema (PIX, transferência) e confirma aqui."""
    with transaction.atomic():
        refund = (
            Refund.objects.for_organization(organization_id)
            .select_for_update()
            .select_related("payment")
            .get(id=refund_id)
        )
        if refund.status != RefundStatus.PENDING or refund.payment.method != PaymentMethod.MANUAL:
            raise RefundNotManual()
        refund.requested_by_id = refund.requested_by_id or actor_id
        _complete(refund)
    return refund
