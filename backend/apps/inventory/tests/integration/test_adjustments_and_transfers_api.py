from typing import Any

import pytest

from apps.identity.domain.permissions import Role
from apps.identity.models import User
from apps.identity.tests.factories import authenticated_client, make_user
from apps.inventory.models import StockItem, StockMovement
from apps.inventory.tests.factories import make_stock_item, make_warehouse

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def operator() -> User:
    return make_user(role=Role.WAREHOUSE)


def _adjust(
    user: User, item: StockItem, counted: int, expected: int, reason: str = "Inventário mensal"
) -> Any:
    return authenticated_client(user).post(
        "/api/v1/inventory/adjustments",
        {
            "stock_item_id": str(item.id),
            "counted_quantity": counted,
            "expected_on_hand": expected,
            "reason": reason,
        },
    )


# ---------------------------------------------------------------------------
# Ajustes
# ---------------------------------------------------------------------------


def test_adjustment_records_the_difference_and_reason(operator: User) -> None:
    item = make_stock_item(warehouse=make_warehouse(organization=operator.organization), on_hand=10)

    response = _adjust(operator, item, counted=7, expected=10, reason="Avaria na prateleira 3")

    assert response.status_code == 200
    assert (response.json()["on_hand"], response.json()["available"]) == (7, 7)
    movement = StockMovement.objects.get(stock_item=item)
    assert (movement.type, movement.on_hand_delta, movement.on_hand_after) == ("ADJUSTMENT", -3, 7)
    assert movement.reason == "Avaria na prateleira 3"


def test_adjustment_rejects_a_count_made_before_another_movement(operator: User) -> None:
    item = make_stock_item(warehouse=make_warehouse(organization=operator.organization), on_hand=10)

    # Pessoa viu 12 na tela, mas o saldo atual é 10 (houve saída durante a contagem).
    response = _adjust(operator, item, counted=8, expected=12)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "STOCK_CHANGED_SINCE_COUNT"
    item.refresh_from_db()
    assert item.on_hand == 10


def test_adjustment_cannot_go_below_reserved(operator: User) -> None:
    item = make_stock_item(
        warehouse=make_warehouse(organization=operator.organization), on_hand=10, reserved=6
    )

    response = _adjust(operator, item, counted=5, expected=10)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_ADJUSTMENT"


def test_matching_count_does_not_create_a_movement(operator: User) -> None:
    item = make_stock_item(warehouse=make_warehouse(organization=operator.organization), on_hand=4)

    response = _adjust(operator, item, counted=4, expected=4)

    assert response.status_code == 200
    assert not StockMovement.objects.exists()


def test_adjustment_requires_a_meaningful_reason(operator: User) -> None:
    item = make_stock_item(warehouse=make_warehouse(organization=operator.organization), on_hand=4)

    response = _adjust(operator, item, counted=3, expected=4, reason="ok")

    assert response.status_code == 400
    assert "reason" in response.json()["error"]["details"]["fields"]


def test_adjusting_another_organization_item_is_not_found(operator: User) -> None:
    foreign = make_stock_item(on_hand=10)

    response = _adjust(operator, foreign, counted=0, expected=10)

    assert response.status_code == 404
    foreign.refresh_from_db()
    assert foreign.on_hand == 10


@pytest.mark.parametrize(
    ("role", "allowed"),
    [(Role.WAREHOUSE, True), (Role.MANAGER, True), (Role.SALES, False), (Role.FINANCE, False)],
)
def test_adjusting_requires_inventory_adjust(role: Role, allowed: bool) -> None:
    user = make_user(role=role)
    item = make_stock_item(warehouse=make_warehouse(organization=user.organization), on_hand=5)

    assert _adjust(user, item, counted=4, expected=5).status_code == (200 if allowed else 403)


# ---------------------------------------------------------------------------
# Transferências
# ---------------------------------------------------------------------------


def _transfer(user: User, item: StockItem, to_warehouse_id: str, quantity: int) -> Any:
    return authenticated_client(user).post(
        "/api/v1/inventory/transfers",
        {"stock_item_id": str(item.id), "to_warehouse_id": to_warehouse_id, "quantity": quantity},
    )


def test_transfer_moves_available_units_and_creates_destination_item(operator: User) -> None:
    origin = make_warehouse(organization=operator.organization, code="CD-SP")
    destination = make_warehouse(organization=operator.organization, code="CD-RJ")
    item = make_stock_item(warehouse=origin, on_hand=10, reserved=2)

    response = _transfer(operator, item, str(destination.id), 8)

    assert response.status_code == 201
    body = response.json()
    assert (body["source"]["on_hand"], body["source"]["available"]) == (2, 0)
    assert body["destination"]["on_hand"] == 8
    movements = StockMovement.objects.filter(reference_id=body["transfer_id"])
    assert sorted(movements.values_list("on_hand_delta", flat=True)) == [-8, 8]
    assert set(movements.values_list("type", flat=True)) == {"TRANSFER"}


def test_transfer_cannot_move_reserved_units(operator: User) -> None:
    origin = make_warehouse(organization=operator.organization)
    destination = make_warehouse(organization=operator.organization)
    item = make_stock_item(warehouse=origin, on_hand=10, reserved=8)

    response = _transfer(operator, item, str(destination.id), 3)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INSUFFICIENT_STOCK"
    assert response.json()["error"]["details"] == {"requested": 3, "available": 2}
    assert not StockMovement.objects.exists()


def test_transfer_to_same_or_inactive_warehouse_is_rejected(operator: User) -> None:
    origin = make_warehouse(organization=operator.organization)
    closed = make_warehouse(organization=operator.organization, is_active=False)
    item = make_stock_item(warehouse=origin, on_hand=10)

    same = _transfer(operator, item, str(origin.id), 1)
    inactive = _transfer(operator, item, str(closed.id), 1)
    foreign = _transfer(operator, item, str(make_warehouse().id), 1)

    assert same.json()["error"]["code"] == "SAME_WAREHOUSE_TRANSFER"
    assert inactive.json()["error"]["code"] == "WAREHOUSE_INACTIVE"
    assert foreign.json()["error"]["code"] == "WAREHOUSE_NOT_FOUND"
