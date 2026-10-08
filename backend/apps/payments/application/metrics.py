"""Cobranças de cartão sem resposta do provedor (aguardando reconciliação), lidas na coleta."""

from collections.abc import Iterable

from apps.payments.domain.status import PaymentMethod, PaymentStatus
from apps.payments.models import Payment
from shared.observability.metrics import GaugeSample, register_gauges


def _pending() -> Iterable[GaugeSample]:
    pending = Payment.objects.filter(status=PaymentStatus.PENDING, method=PaymentMethod.CARD)
    yield {}, float(pending.count())


def register() -> None:
    register_gauges(
        "orderflow_payments_awaiting_reconciliation",
        "Cobranças de cartão PENDING (sem resposta do provedor)",
        [],
        _pending,
    )
