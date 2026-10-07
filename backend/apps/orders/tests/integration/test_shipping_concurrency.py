"""Despachos simultâneos do mesmo pedido: uma remessa, uma baixa de estoque."""

import threading
import time
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import pytest
from django.db import connection

from apps.identity.domain.permissions import Role
from apps.identity.tests.factories import authenticated_client
from apps.inventory.models import StockItem, StockMovement
from apps.orders.tests.factories import ORDERS, Scenario, make_scenario
from apps.shipping.domain.provider import Label
from apps.shipping.infrastructure.fake_provider import FakeShippingProvider
from apps.shipping.models import Shipment

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
def slow_carrier(monkeypatch: pytest.MonkeyPatch) -> None:
    """Transportadora lenta: os dois despachos passam da checagem inicial antes de gravar."""
    original = FakeShippingProvider.create_shipment

    def slow(self: Any, **kwargs: Any) -> Label:
        time.sleep(0.5)
        return original(self, **kwargs)

    monkeypatch.setattr(FakeShippingProvider, "create_shipment", slow)


def _ready_order() -> tuple[Scenario, str]:
    s = make_scenario(role=Role.MANAGER)
    s.stock(s.cola, 10)
    s.stock(s.water, 10)
    order_id = str(s.place().json()["id"])
    s.client.post(
        f"{ORDERS}/{order_id}/pay",
        {"card_token": "tok_approved"},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    s.client.post(f"{ORDERS}/{order_id}/start-picking")
    s.client.post(f"{ORDERS}/{order_id}/complete-picking")
    return s, order_id


def _shipper(s: Scenario, order_id: str) -> Callable[[], tuple[int, str]]:
    def ship() -> tuple[int, str]:
        response = authenticated_client(s.user).post(f"{ORDERS}/{order_id}/ship")
        body = response.json()
        return response.status_code, body.get("status") or body["error"]["code"]

    return ship


@pytest.mark.usefixtures("slow_carrier")
def test_two_dispatches_at_once_ship_once() -> None:
    s, order_id = _ready_order()

    outcomes = _run_concurrently(_shipper(s, order_id), _shipper(s, order_id))

    assert outcomes == [(200, "SHIPPED"), (200, "SHIPPED")]
    assert Shipment.objects.filter(order_id=order_id).count() == 1
    assert StockMovement.objects.filter(type="SALE").count() == 2  # uma por linha
    cola = StockItem.objects.get(warehouse=s.warehouse, product=s.cola)
    assert (cola.on_hand, cola.reserved) == (8, 0)
