from datetime import timedelta

from apps.payments.domain.exceptions import InvalidPaymentTransition
from apps.payments.domain.status import PaymentStatus, RefundStatus

P, R = PaymentStatus, RefundStatus

_PAYMENT: dict[PaymentStatus, frozenset[PaymentStatus]] = {
    P.PENDING: frozenset({P.APPROVED, P.DECLINED, P.FAILED}),
    P.APPROVED: frozenset({P.REFUNDED}),
    P.DECLINED: frozenset(),
    P.FAILED: frozenset(),
    P.REFUNDED: frozenset(),
}
_REFUND: dict[RefundStatus, frozenset[RefundStatus]] = {
    R.PENDING: frozenset({R.SUCCEEDED, R.FAILED}),
    R.FAILED: frozenset({R.PENDING}),  # nova tentativa pelo financeiro
    R.SUCCEEDED: frozenset(),
}


def assert_payment_transition(source: PaymentStatus, target: PaymentStatus) -> None:
    if target not in _PAYMENT[source]:
        raise InvalidPaymentTransition(details={"from": source.value, "to": target.value})


def assert_refund_transition(source: RefundStatus, target: RefundStatus) -> None:
    if target not in _REFUND[source]:
        raise InvalidPaymentTransition(details={"from": source.value, "to": target.value})


def reconciliation_delay(attempts: int) -> timedelta:
    """Backoff exponencial para consultar o provedor: 1, 2, 4... minutos, no máximo 60."""
    return timedelta(minutes=min(2**attempts, 60))
