"""O banco protege o estoque mesmo contra código que contorne o domínio (ADR-004)."""

from uuid import UUID, uuid4

import pytest
from django.db import DatabaseError, IntegrityError, transaction
from django.utils import timezone

from apps.inventory.domain.movements import MovementType
from apps.inventory.models import StockItem, StockMovement, StockReservation
from apps.inventory.tests.factories import make_stock_item

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _movement(item: StockItem) -> StockMovement:
    return StockMovement.objects.create(
        organization=item.organization,
        stock_item=item,
        type=MovementType.PURCHASE,
        on_hand_delta=1,
        reserved_delta=0,
        on_hand_after=1,
        reserved_after=0,
    )


def test_movements_cannot_be_updated() -> None:
    movement = _movement(make_stock_item(on_hand=1))

    with pytest.raises(DatabaseError, match="append-only"), transaction.atomic():
        StockMovement.objects.filter(id=movement.id).update(on_hand_delta=100)


def test_movements_cannot_be_deleted() -> None:
    movement = _movement(make_stock_item(on_hand=1))

    with pytest.raises(DatabaseError, match="append-only"), transaction.atomic():
        StockMovement.objects.filter(id=movement.id).delete()


@pytest.mark.parametrize(
    ("on_hand", "reserved"),
    [(-1, 0), (5, -1), (5, 6)],  # I1, I2, I3 (reserved > on_hand)
)
def test_balance_invariants_are_enforced_by_the_database(on_hand: int, reserved: int) -> None:
    item = make_stock_item(on_hand=5)

    with pytest.raises(IntegrityError), transaction.atomic():
        StockItem.objects.filter(id=item.id).update(on_hand=on_hand, reserved=reserved)


def test_one_stock_item_per_product_and_warehouse() -> None:  # I4
    item = make_stock_item(on_hand=1)

    with pytest.raises(IntegrityError), transaction.atomic():
        make_stock_item(warehouse=item.warehouse, product=item.product)


def test_available_is_computed_by_the_database() -> None:
    item = make_stock_item(on_hand=10, reserved=4)

    StockItem.objects.filter(id=item.id).update(reserved=1)
    item.refresh_from_db()

    assert item.available == 9


def test_movement_must_change_something() -> None:
    item = make_stock_item(on_hand=1)

    with pytest.raises(IntegrityError), transaction.atomic():
        StockMovement.objects.create(
            organization=item.organization,
            stock_item=item,
            type=MovementType.ADJUSTMENT,
            on_hand_delta=0,
            reserved_delta=0,
            on_hand_after=1,
            reserved_after=0,
        )


def _reservation(item: StockItem, line_id: UUID, **kwargs: object) -> None:
    StockReservation.objects.create(
        organization=item.organization,
        stock_item=item,
        order_id=uuid4(),
        order_line_id=line_id,
        expires_at=timezone.now(),
        **{"quantity": 1, "status": "ACTIVE", **kwargs},
    )


def test_one_holding_reservation_per_order_line_and_item() -> None:  # I8
    item, line = make_stock_item(on_hand=5), uuid4()
    _reservation(item, line)
    _reservation(item, line, status="RELEASED")  # encerradas não contam

    with pytest.raises(IntegrityError), transaction.atomic():
        _reservation(item, line, status="CONFIRMED")


def test_reservation_quantity_must_be_positive() -> None:  # I5
    with pytest.raises(IntegrityError), transaction.atomic():
        _reservation(make_stock_item(on_hand=5), uuid4(), quantity=0)
