"""Cobranças simultâneas do mesmo pedido: nunca duas cobranças (ADR-012, P1/P2)."""

import threading
import time
from collections.abc import Callable
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from django.db import connection

from apps.identity.tests.factories import authenticated_client
from apps.orders.tests.factories import ORDERS, Scenario, make_scenario
from apps.payments.domain.gateway import ChargeResult
from apps.payments.infrastructure.fake_gateway import FakePaymentGateway
from apps.payments.models import Payment

pytestmark = [pytest.mark.concurrency, pytest.mark.django_db(transaction=True)]


def _run_concurrently(*tasks: Callable[[], Any]) -> list[Any]:
    barrier = threading.Barrier(len(tasks))
    outcomes: list[Any] = []

    def runner(task: Callable[[], Any]) -> None:
        try:
            barrier.wait()
            outcomes.append(task())
        except Exception as exc:
            outcomes.append(type(exc).__name__)
        finally:
            connection.close()

    threads = [threading.Thread(target=runner, args=(task,)) for task in tasks]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return outcomes


@pytest.fixture
def slow_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provedor lento: a cobrança fica "em voo" tempo suficiente para a disputa."""
    original = FakePaymentGateway.charge

    def slow_charge(self: Any, **kwargs: Any) -> ChargeResult:
        time.sleep(0.5)
        return original(self, **kwargs)

    monkeypatch.setattr(FakePaymentGateway, "charge", slow_charge)


def _payer(s: Scenario, order_id: str, key: UUID) -> Callable[[], tuple[int, str]]:
    def pay() -> tuple[int, str]:
        response = authenticated_client(s.user).post(
            f"{ORDERS}/{order_id}/pay",
            {"card_token": "tok_approved"},
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(key),
        )
        body = response.json()
        return response.status_code, body.get("status") or body["error"]["code"]

    return pay


def _awaiting_order() -> tuple[Scenario, str]:
    s = make_scenario()
    s.stock(s.cola, 10)
    s.stock(s.water, 10)
    return s, str(s.place().json()["id"])


@pytest.mark.usefixtures("slow_gateway")
def test_same_key_twice_at_once_charges_once() -> None:
    s, order_id = _awaiting_order()
    key = uuid4()

    outcomes = _run_concurrently(_payer(s, order_id, key), _payer(s, order_id, key))

    assert sorted(outcomes) == [(200, "PAID"), (409, "IDEMPOTENCY_REQUEST_IN_PROGRESS")]
    assert Payment.objects.filter(order_id=order_id).count() == 1


@pytest.mark.usefixtures("slow_gateway")
def test_two_payment_attempts_at_once_charge_once() -> None:
    s, order_id = _awaiting_order()

    outcomes = _run_concurrently(_payer(s, order_id, uuid4()), _payer(s, order_id, uuid4()))

    assert sorted(outcomes) == [(200, "PAID"), (409, "PAYMENT_IN_PROGRESS")]
    assert list(Payment.objects.values_list("status", "amount")) == [("APPROVED", Decimal("13.00"))]
