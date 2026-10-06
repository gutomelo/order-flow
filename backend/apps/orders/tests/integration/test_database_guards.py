"""O banco protege as invariantes do pedido mesmo contra código que contorne o domínio."""

from decimal import Decimal

import pytest
from django.db import DatabaseError, IntegrityError, transaction

from apps.orders.models import Order, OrderLine, OrderStatusHistory
from apps.orders.tests.factories import make_scenario

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def order() -> Order:
    s = make_scenario()
    return Order.objects.get(id=s.place().json()["id"])


def test_history_cannot_be_rewritten(order: Order) -> None:  # O9
    entry = OrderStatusHistory.objects.filter(order=order)

    with pytest.raises(DatabaseError, match="append-only"), transaction.atomic():
        entry.update(reason="apagando rastros")
    with pytest.raises(DatabaseError, match="append-only"), transaction.atomic():
        entry.delete()


def test_line_total_must_match_quantity_times_price(order: Order) -> None:  # O4
    with pytest.raises(IntegrityError), transaction.atomic():
        OrderLine.objects.filter(order=order).update(line_total=Decimal("0.01"))


def test_order_total_must_match_its_parts(order: Order) -> None:  # O5
    with pytest.raises(IntegrityError), transaction.atomic():
        Order.objects.filter(id=order.id).update(total=Decimal("1.00"))


def test_a_product_appears_once_per_order(order: Order) -> None:  # O8
    line = OrderLine.objects.filter(order=order).first()
    assert line is not None
    line.pk = None
    line.position = 99

    with pytest.raises(IntegrityError), transaction.atomic():
        line.save(force_insert=True)


def test_submitted_orders_keep_number_and_snapshot(order: Order) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        Order.objects.filter(id=order.id).update(number=None)
    with pytest.raises(IntegrityError), transaction.atomic():
        Order.objects.filter(id=order.id).update(shipping_snapshot=None)


def test_awaiting_payment_always_has_a_due_date(order: Order) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        Order.objects.filter(id=order.id).update(status="AWAITING_PAYMENT", payment_due_at=None)
