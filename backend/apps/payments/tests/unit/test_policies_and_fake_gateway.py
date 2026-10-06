from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from apps.payments.domain.exceptions import InvalidPaymentTransition
from apps.payments.domain.gateway import GatewayUnavailable
from apps.payments.domain.policies import (
    assert_payment_transition,
    assert_refund_transition,
    reconciliation_delay,
)
from apps.payments.domain.status import PaymentStatus as P
from apps.payments.domain.status import RefundStatus as R
from apps.payments.infrastructure.fake_gateway import FakePaymentGateway

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("source", "target"),
    [(P.APPROVED, P.PENDING), (P.DECLINED, P.APPROVED), (P.REFUNDED, P.APPROVED),
     (P.PENDING, P.REFUNDED)],
)  # fmt: skip
def test_payments_never_go_back(source: P, target: P) -> None:
    with pytest.raises(InvalidPaymentTransition):
        assert_payment_transition(source, target)


def test_only_failed_refunds_go_back_to_pending() -> None:
    assert_refund_transition(R.FAILED, R.PENDING)
    with pytest.raises(InvalidPaymentTransition):
        assert_refund_transition(R.SUCCEEDED, R.PENDING)


def test_reconciliation_backs_off_up_to_an_hour() -> None:
    assert [reconciliation_delay(n) for n in (0, 1, 3, 10)] == [
        timedelta(minutes=1),
        timedelta(minutes=2),
        timedelta(minutes=8),
        timedelta(minutes=60),
    ]


@pytest.mark.django_db  # cache em memória dos testes
def test_fake_gateway_is_idempotent_and_remembers_timeouts() -> None:
    gateway, key = FakePaymentGateway(), uuid4()

    with pytest.raises(GatewayUnavailable):
        gateway.charge(
            idempotency_key=key, amount=Decimal(10), currency="BRL", card_token="tok_timeout"
        )
    found = gateway.get_charge(idempotency_key=key)
    again = gateway.charge(
        idempotency_key=key, amount=Decimal(10), currency="BRL", card_token="tok_declined"
    )

    assert found is not None and found.status == "APPROVED"  # o provedor processou
    assert again == found  # mesma chave, mesmo resultado (não cobra de novo)
    assert gateway.get_charge(idempotency_key=uuid4()) is None
