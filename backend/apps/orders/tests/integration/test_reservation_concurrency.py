"""Cenários obrigatórios de reserva (ADR-008; critério de conclusão da Phase 7).

Threads com conexões próprias e barreira para que as transações realmente disputem as linhas.
"""

import threading
import time
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from django.db import connection, transaction
from django.test import override_settings
from django.utils import timezone

from apps.identity.tests.factories import authenticated_client
from apps.inventory.application.reconciliation import find_divergences
from apps.inventory.models import StockItem, StockMovement, StockReservation
from apps.orders.application.commands.cancel_order import cancel_order
from apps.orders.application.commands.expiration import expire_unpaid_order
from apps.orders.models import Order
from apps.orders.tests.factories import ORDERS, Scenario, make_scenario

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


def _pending_order(s: Scenario, lines: list[tuple[Any, int]]) -> str:
    """Pedido PENDING criado sem estoque. A disputa acontece depois, no `POST /reserve`.

    Por que não disputar via `POST /orders`: toda submissão trava o contador de números da
    organização, o que já as serializa — o lock dos itens nem seria exercitado (descoberto ao
    remover esse lock e ver o teste continuar verde). Reserva explícita, cancelamento e expiração
    não passam pelo contador: ali o lock dos itens é a única proteção.
    """
    payload = s.payload(lines=[{"product_id": str(p.id), "quantity": q} for p, q in lines])
    body = s.place(payload).json()
    assert body["status"] == "PENDING"
    return str(body["id"])


def _reserver(s: Scenario, order_id: str) -> Callable[[], str]:
    def reserve() -> str:
        response = authenticated_client(s.user).post(f"{ORDERS}/{order_id}/reserve")
        body = response.json()
        return str(body["status"] if response.status_code == 200 else body["error"]["code"])

    return reserve


def test_the_last_unit_is_never_reserved_twice() -> None:
    """available = 1 e duas reservas simultâneas de 1: exatamente uma vence."""
    s = make_scenario()
    first = _pending_order(s, [(s.cola, 1)])
    second = _pending_order(s, [(s.cola, 1)])
    item = s.stock(s.cola, 1)

    outcomes = _run_concurrently(_reserver(s, first), _reserver(s, second))

    assert sorted(outcomes) == ["AWAITING_PAYMENT", "INSUFFICIENT_STOCK"]
    item.refresh_from_db()
    assert (item.reserved, item.available) == (1, 0)
    assert StockReservation.objects.filter(status="ACTIVE").count() == 1
    assert StockMovement.objects.filter(type="RESERVATION").count() == 1


def test_orders_locking_the_same_items_in_opposite_line_order_do_not_deadlock() -> None:
    s = make_scenario()
    orders = [
        _pending_order(s, [(s.cola, 1), (s.water, 1)]),
        _pending_order(s, [(s.water, 1), (s.cola, 1)]),
        _pending_order(s, [(s.cola, 2), (s.water, 2)]),
        _pending_order(s, [(s.water, 2), (s.cola, 2)]),
    ]
    s.stock(s.cola, 50)
    s.stock(s.water, 50)

    outcomes = _run_concurrently(*[_reserver(s, order_id) for order_id in orders])

    assert outcomes == ["AWAITING_PAYMENT"] * 4
    assert StockItem.objects.get(product=s.cola).reserved == 6


def test_cancel_and_expiration_racing_release_the_stock_once() -> None:
    s = make_scenario()
    s.stock(s.cola, 10)
    s.stock(s.water, 10)
    order_id = s.place().json()["id"]
    Order.objects.filter(id=order_id).update(payment_due_at=timezone.now() - timedelta(seconds=1))

    outcomes = _run_concurrently(
        lambda: cancel_order(s.organization_id, s.user.id, order_id, reason="Cliente desistiu"),
        lambda: expire_unpaid_order(order_id, now=timezone.now()),
    )

    assert len(outcomes) == 2
    assert StockItem.objects.get(product=s.cola).reserved == 0
    assert StockMovement.objects.filter(type="RELEASE").count() == 2  # uma por linha, uma vez
    assert find_divergences() == []


@override_settings(STOCK_LOCK_TIMEOUT_MS=200)
def test_a_long_held_item_lock_turns_into_stock_busy() -> None:
    """Outra transação segura o item; a reserva desiste rápido em vez de enfileirar requisições."""
    s = make_scenario()
    item = s.stock(s.cola, 10)
    # Pedido PENDING (pediu mais do que havia); depois chega estoque e alguém tenta reservar.
    pending = s.place(s.payload(lines=[{"product_id": str(s.cola.id), "quantity": 99}])).json()
    pending_id = pending["id"]
    StockItem.objects.filter(id=item.id).update(on_hand=200)
    holding = threading.Event()
    done = threading.Event()

    def hold_lock() -> str:
        with transaction.atomic():
            StockItem.objects.select_for_update().get(id=item.id)
            holding.set()
            done.wait(timeout=5)
        return "held"

    def reserve() -> tuple[int, str]:
        holding.wait(timeout=5)
        try:
            response = authenticated_client(s.user).post(f"{ORDERS}/{pending_id}/reserve")
            return response.status_code, response.json()["error"]["code"]
        finally:
            done.set()

    started = time.monotonic()
    outcomes = _run_concurrently(hold_lock, reserve)

    assert (409, "STOCK_BUSY") in outcomes
    assert time.monotonic() - started < 3
    assert Order.objects.get(id=pending_id).status == "PENDING"
