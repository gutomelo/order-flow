"""Concorrência de pedidos (docs/domain/orders.md#concorrência)."""

import threading
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import pytest
from django.db import connection

from apps.identity.tests.factories import authenticated_client
from apps.orders.models import Order, OrderStatusHistory
from apps.orders.tests.factories import ORDERS, make_scenario

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


def test_concurrent_submissions_of_a_draft_number_it_once() -> None:
    s = make_scenario()
    order_id = s.draft().json()["id"]

    def submit() -> tuple[int, Any]:
        # Cliente HTTP por thread: o APIClient não é thread-safe.
        response = authenticated_client(s.user).post(f"{ORDERS}/{order_id}/submit")
        return response.status_code, response.json()["number"]

    outcomes = _run_concurrently(submit, submit, submit)

    assert outcomes == [(200, 1)] * 3
    assert OrderStatusHistory.objects.filter(order_id=order_id, to_status="PENDING").count() == 1


def test_concurrent_orders_get_distinct_contiguous_numbers() -> None:
    s = make_scenario()

    def place() -> int:
        client = authenticated_client(s.user)
        response = client.post(
            ORDERS, s.payload(), format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4())
        )
        return int(response.json()["number"])

    numbers = _run_concurrently(*[place] * 5)

    assert sorted(numbers) == [1, 2, 3, 4, 5]


def test_concurrent_requests_with_the_same_key_create_one_order() -> None:
    s = make_scenario()
    key = str(uuid4())

    def place() -> tuple[int, str]:
        client = authenticated_client(s.user)
        response = client.post(ORDERS, s.payload(), format="json", HTTP_IDEMPOTENCY_KEY=key)
        return response.status_code, response.json()["id"]

    outcomes = _run_concurrently(place, place, place)

    assert {status for status, _ in outcomes} == {201}
    assert len({order_id for _, order_id in outcomes}) == 1
    assert Order.objects.count() == 1
