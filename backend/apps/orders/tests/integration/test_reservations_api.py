"""Reserva de estoque no ciclo do pedido (Phase 7, docs/domain/orders.md e inventory.md)."""

from datetime import datetime, timedelta

import pytest
from django.utils import timezone

from apps.catalog.models import Product
from apps.catalog.tests.factories import make_product
from apps.inventory.application.reconciliation import find_divergences
from apps.inventory.models import StockItem, StockMovement, StockReservation
from apps.inventory.tasks import reconcile_stock
from apps.orders.application.commands.expiration import (
    cancel_stale_pending_orders,
    expire_due_orders,
)
from apps.orders.models import Order
from apps.orders.tasks import expire_unpaid_orders
from apps.orders.tests.factories import ORDERS, Scenario, make_scenario
from apps.pricing.tests.factories import set_price

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def s() -> Scenario:
    scenario = make_scenario()
    scenario.stock(scenario.cola, 10)
    scenario.stock(scenario.water, 10)
    return scenario


def _item(s: Scenario, product: Product) -> StockItem:
    return StockItem.objects.get(warehouse=s.warehouse, product=product)


def test_order_with_stock_reserves_every_line_and_awaits_payment(s: Scenario) -> None:
    before = timezone.now()

    body = s.place().json()

    assert body["status"] == "AWAITING_PAYMENT"
    due = datetime.fromisoformat(body["payment_due_at"])
    assert timedelta(hours=47) < due - before < timedelta(hours=49)  # 48 h por padrão
    assert [(h["from_status"], h["to_status"]) for h in body["history"]] == [
        (None, "PENDING"),
        ("PENDING", "AWAITING_PAYMENT"),
    ]
    cola = _item(s, s.cola)
    assert (cola.on_hand, cola.reserved, cola.available) == (10, 2, 8)
    reservations = StockReservation.objects.filter(order_id=body["id"])
    assert sorted((r.quantity, r.status) for r in reservations) == [(2, "ACTIVE"), (3, "ACTIVE")]
    movement = StockMovement.objects.get(stock_item=cola, type="RESERVATION")
    assert (movement.reserved_delta, movement.reference_id) == (2, reservations[0].order_id)
    assert find_divergences() == []


def test_without_stock_for_one_line_the_order_stays_pending_and_nothing_is_reserved(
    s: Scenario,
) -> None:
    payload = s.payload(
        lines=[
            {"product_id": str(s.cola.id), "quantity": 2},
            {"product_id": str(s.water.id), "quantity": 11},  # só há 10
        ]
    )

    body = s.place(payload).json()

    assert (body["status"], body["number"], body["payment_due_at"]) == ("PENDING", 1, None)
    assert _item(s, s.cola).reserved == 0  # tudo-ou-nada: a linha que cabia também não reservou
    assert not StockReservation.objects.exists()
    assert not StockMovement.objects.filter(type="RESERVATION").exists()


def test_explicit_reservation_lists_every_shortage_and_works_after_receiving_stock(
    s: Scenario,
) -> None:
    order_id = s.place(s.payload(lines=[{"product_id": str(s.water.id), "quantity": 15}])).json()[
        "id"
    ]

    refused = s.client.post(f"{ORDERS}/{order_id}/reserve")
    StockItem.objects.filter(warehouse=s.warehouse, product=s.water).update(on_hand=20)
    accepted = s.client.post(f"{ORDERS}/{order_id}/reserve")
    again = s.client.post(f"{ORDERS}/{order_id}/reserve")

    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "INSUFFICIENT_STOCK"
    assert refused.json()["error"]["details"] == {
        "lines": [{"product_id": str(s.water.id), "requested": 15, "available": 10}]
    }
    assert accepted.json()["status"] == "AWAITING_PAYMENT"
    assert again.status_code == 200  # idempotente por estado
    assert StockReservation.objects.filter(order_id=order_id).count() == 1


def test_a_product_never_stocked_in_the_warehouse_counts_as_zero(s: Scenario) -> None:
    juice = make_product(organization=s.user.organization)
    set_price(s.price_list, juice, "5.00")

    body = s.place(s.payload(lines=[{"product_id": str(juice.id), "quantity": 1}])).json()

    assert body["status"] == "PENDING"


def test_cancelling_a_reserved_order_gives_the_stock_back(s: Scenario) -> None:
    order_id = s.place().json()["id"]

    body = s.client.post(f"{ORDERS}/{order_id}/cancel", {"reason": "Cliente desistiu"}).json()

    assert (body["status"], body["payment_due_at"]) == ("CANCELLED", None)
    assert _item(s, s.cola).reserved == 0
    assert set(StockReservation.objects.values_list("status", flat=True)) == {"RELEASED"}
    assert StockMovement.objects.filter(type="RELEASE").count() == 2
    assert find_divergences() == []


def test_expired_reservations_return_the_order_to_pending(s: Scenario) -> None:
    expired_id = s.place().json()["id"]
    current_id = s.place().json()["id"]
    Order.objects.filter(id=expired_id).update(payment_due_at=timezone.now() - timedelta(minutes=1))

    first_run = expire_due_orders()
    second_run = expire_due_orders()

    assert (first_run, second_run) == (1, 0)
    expired = s.client.get(f"{ORDERS}/{expired_id}").json()
    assert (expired["status"], expired["payment_due_at"]) == ("PENDING", None)
    assert expired["history"][-1]["reason"] == "Reserva expirada sem pagamento"
    assert expired["history"][-1]["changed_by"] is None  # sistema
    assert StockReservation.objects.filter(order_id=expired_id, status="EXPIRED").count() == 2
    assert s.client.get(f"{ORDERS}/{current_id}").json()["status"] == "AWAITING_PAYMENT"
    assert _item(s, s.cola).reserved == 2  # só a reserva do pedido ainda válido
    assert find_divergences() == []


def test_stale_pending_orders_are_cancelled(s: Scenario) -> None:
    no_stock = s.payload(lines=[{"product_id": str(s.water.id), "quantity": 99}])
    stale_id = s.place(no_stock).json()["id"]
    recent_id = s.place(no_stock).json()["id"]
    Order.objects.filter(id=stale_id).update(updated_at=timezone.now() - timedelta(days=8))

    assert cancel_stale_pending_orders() == 1

    stale = s.client.get(f"{ORDERS}/{stale_id}").json()
    assert stale["status"] == "CANCELLED"
    assert stale["history"][-1]["reason"].startswith("PENDING_TIMEOUT")
    assert s.client.get(f"{ORDERS}/{recent_id}").json()["status"] == "PENDING"


def test_submitting_a_draft_also_reserves(s: Scenario) -> None:
    draft_id = s.draft().json()["id"]

    body = s.client.post(f"{ORDERS}/{draft_id}/submit").json()

    assert body["status"] == "AWAITING_PAYMENT"
    again = s.client.post(f"{ORDERS}/{draft_id}/submit")
    assert again.json()["status"] == "AWAITING_PAYMENT"  # reenviar não reserva de novo
    assert StockReservation.objects.filter(order_id=draft_id).count() == 2


def test_reconciliation_flags_a_reserved_balance_without_reservations(s: Scenario) -> None:
    s.place()
    StockItem.objects.filter(product=s.cola).update(reserved=5)

    divergences = find_divergences()

    assert [(d.field, d.stored, d.expected) for d in divergences] == [("reserved", 5, 2)]


def test_periodic_tasks_run_the_jobs(s: Scenario) -> None:
    order_id = s.place().json()["id"]
    Order.objects.filter(id=order_id).update(payment_due_at=timezone.now() - timedelta(minutes=1))

    expired = expire_unpaid_orders.apply().get()
    divergences = reconcile_stock.apply().get()

    assert (expired, divergences) == (1, 0)
    assert Order.objects.get(id=order_id).status == "PENDING"
