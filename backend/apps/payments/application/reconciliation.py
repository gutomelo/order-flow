"""Cobranças sem resposta (timeout/indisponível): consulta o provedor pela chave de idempotência.

- O provedor conhece a cobrança → aplica o resultado (aprovada/recusada).
- O provedor responde que **não** conhece → nada foi cobrado: `FAILED` na hora, e o pedido pode
  ser pago de novo (só um `PENDING` por pedido, P2 — esperar horas bloquearia o cliente).
- O provedor não responde à consulta → não dá para saber: nova consulta com backoff, e `FAILED`
  após `PAYMENT_RECONCILIATION_MAX_ATTEMPTS`.
"""

from datetime import datetime
from uuid import UUID

import structlog
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.payments.application.charges import settle
from apps.payments.domain.gateway import GatewayUnavailable
from apps.payments.domain.policies import reconciliation_delay
from apps.payments.domain.status import PaymentMethod, PaymentStatus
from apps.payments.infrastructure.gateways import get_payment_gateway
from apps.payments.models import Payment

logger = structlog.get_logger(__name__)

BATCH_SIZE = 100


def reconcile_payment(payment_id: UUID, *, now: datetime) -> str:
    payment = Payment.objects.get(id=payment_id)
    if payment.status != PaymentStatus.PENDING:
        return payment.status
    try:  # consulta fora de transação (I/O externo)
        result = get_payment_gateway().get_charge(idempotency_key=payment.idempotency_key)
        provider_answered = True
    except GatewayUnavailable:
        result, provider_answered = None, False
    if result is not None:
        return settle(payment.id, result).status
    with transaction.atomic():
        locked = (
            Payment.objects.select_for_update(skip_locked=True)
            .filter(id=payment_id, status=PaymentStatus.PENDING)
            .first()
        )
        if locked is None:
            return PaymentStatus.PENDING
        locked.attempts += 1
        gave_up = locked.attempts >= settings.PAYMENT_RECONCILIATION_MAX_ATTEMPTS
        if provider_answered or gave_up:
            locked.status = PaymentStatus.FAILED
            locked.completed_at = now
            locked.next_attempt_at = None
            logger.warning(
                "payments.payment.failed",
                payment_id=str(payment_id),
                cause="not_found_at_provider" if provider_answered else "provider_unreachable",
            )
        else:
            locked.next_attempt_at = now + reconciliation_delay(locked.attempts)
        locked.save()
        return locked.status


def reconcile_pending_payments(now: datetime | None = None) -> int:
    now = now or timezone.now()
    due = Payment.objects.filter(
        status=PaymentStatus.PENDING, method=PaymentMethod.CARD, next_attempt_at__lte=now
    ).values_list("id", flat=True)[:BATCH_SIZE]
    statuses = [reconcile_payment(payment_id, now=now) for payment_id in list(due)]
    resolved = sum(status != PaymentStatus.PENDING for status in statuses)
    if statuses:
        logger.info("payments.reconciliation.run", checked=len(statuses), resolved=resolved)
    return resolved
