"""Cobranças (docs/domain/payments.md). `orders` coordena; aqui só pagamento e gateway."""

from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import structlog
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.payments.domain.events import PaymentApproved
from apps.payments.domain.exceptions import PaymentInProgress
from apps.payments.domain.gateway import ChargeResult, GatewayUnavailable
from apps.payments.domain.policies import assert_payment_transition
from apps.payments.domain.status import PaymentMethod, PaymentStatus
from apps.payments.infrastructure.gateways import get_payment_gateway
from apps.payments.models import Payment
from shared.events.bus import publish

logger = structlog.get_logger(__name__)

# A reconciliação só olha uma cobrança depois disso: a chamada síncrona tem prioridade.
FIRST_RECONCILIATION_AFTER = timedelta(minutes=1)


def create_pending_card_payment(
    organization_id: UUID,
    actor_id: UUID,
    *,
    order_id: UUID,
    order_reference: str,
    amount: Decimal,
) -> Payment:
    """Registra a intenção ANTES de falar com o gateway (P7): se o processo cair no meio, a
    reconciliação acha o pagamento pela chave de idempotência."""
    try:
        with transaction.atomic():
            return Payment.objects.create(
                organization_id=organization_id,
                order_id=order_id,
                order_reference=order_reference,
                method=PaymentMethod.CARD,
                amount=amount,
                status=PaymentStatus.PENDING,
                next_attempt_at=timezone.now() + FIRST_RECONCILIATION_AFTER,
                created_by_id=actor_id,
            )
    except IntegrityError as exc:  # P2
        raise PaymentInProgress() from exc


def execute_charge(payment_id: UUID, card_token: str) -> Payment:
    """Chama o gateway FORA de transação. O token não é guardado nem logado (P4)."""
    payment = Payment.objects.get(id=payment_id)
    try:
        result = get_payment_gateway().charge(
            idempotency_key=payment.idempotency_key,
            amount=payment.amount,
            currency=payment.currency,
            card_token=card_token,
        )
    except GatewayUnavailable:
        # Resultado desconhecido: fica PENDING para a reconciliação (resposta 202).
        logger.warning("payments.charge.unconfirmed", payment_id=str(payment.id))
        return payment
    return settle(payment.id, result)


def settle(payment_id: UUID, result: ChargeResult) -> Payment:
    """Grava o resultado do provedor. Idempotente: quem chegar depois (síncrono ou reconciliação)
    encontra o pagamento já resolvido e não faz nada."""
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(id=payment_id)
        if payment.status != PaymentStatus.PENDING:
            return payment
        target = PaymentStatus.APPROVED if result.status == "APPROVED" else PaymentStatus.DECLINED
        assert_payment_transition(PaymentStatus(payment.status), target)
        payment.status = target
        payment.provider_reference = result.provider_reference
        payment.decline_reason = result.decline_reason
        payment.completed_at = timezone.now()
        payment.next_attempt_at = None
        payment.save()
        if target == PaymentStatus.APPROVED:
            publish(
                PaymentApproved(
                    organization_id=payment.organization_id,
                    payment_id=payment.id,
                    order_id=payment.order_id,
                )
            )
    logger.info("payments.payment.settled", payment_id=str(payment.id), status=payment.status)
    return payment


def record_manual_payment(
    organization_id: UUID,
    actor_id: UUID,
    *,
    order_id: UUID,
    order_reference: str,
    amount: Decimal,
    reference: str,
) -> Payment:
    """Baixa feita pelo financeiro (boleto/PIX/transferência conciliados fora). Roda na transação
    de quem chama (orders), junto com a mudança do pedido."""
    if Payment.objects.filter(order_id=order_id, status=PaymentStatus.PENDING).exists():
        raise PaymentInProgress()  # um cartão em andamento poderia ser aprovado depois (P1)
    payment = Payment.objects.create(
        organization_id=organization_id,
        order_id=order_id,
        order_reference=order_reference,
        method=PaymentMethod.MANUAL,
        amount=amount,
        status=PaymentStatus.APPROVED,
        manual_reference=reference.strip(),
        completed_at=timezone.now(),
        created_by_id=actor_id,
    )
    publish(
        PaymentApproved(organization_id=organization_id, payment_id=payment.id, order_id=order_id)
    )
    logger.info("payments.payment.recorded_manually", payment_id=str(payment.id))
    return payment
