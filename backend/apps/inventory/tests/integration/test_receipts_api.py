from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.catalog.tests.factories import make_product
from apps.identity.domain.permissions import Role
from apps.identity.models import User
from apps.identity.tests.factories import authenticated_client, make_user
from apps.inventory.models import StockItem, StockMovement, StockReceipt, Warehouse
from apps.inventory.tests.factories import make_warehouse
from apps.suppliers.tests.factories import make_supplier

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def operator() -> User:
    return make_user(role=Role.WAREHOUSE)


@pytest.fixture
def warehouse(operator: User) -> Warehouse:
    return make_warehouse(organization=operator.organization, code="CD-SP")


def _receive(client: APIClient, warehouse: Warehouse, lines: list[dict[str, Any]], **extra: Any):  # type: ignore[no-untyped-def]
    payload = {"warehouse_id": str(warehouse.id), "lines": lines, **extra}
    return client.post("/api/v1/inventory/receipts", payload, format="json")


def test_receipt_creates_stock_items_and_purchase_movements(
    operator: User, warehouse: Warehouse
) -> None:
    coffee = make_product(organization=operator.organization)
    sugar = make_product(organization=operator.organization)
    client = authenticated_client(operator)

    response = _receive(
        client,
        warehouse,
        [
            {"product_id": str(coffee.id), "quantity": 40},
            {"product_id": str(sugar.id), "quantity": 5},
        ],
        document_number="NF-1001",
    )

    assert response.status_code == 201
    item = StockItem.objects.get(product=coffee, warehouse=warehouse)
    assert (item.on_hand, item.reserved, item.available) == (40, 0, 40)
    movement = StockMovement.objects.get(stock_item=item)
    assert (movement.type, movement.on_hand_delta, movement.on_hand_after) == ("PURCHASE", 40, 40)
    assert movement.reference_type == "receipt"
    assert str(movement.reference_id) == response.json()["id"]
    assert movement.performed_by == operator
    assert len(response.json()["movements"]) == 2


def test_second_receipt_adds_to_existing_balance(operator: User, warehouse: Warehouse) -> None:
    product = make_product(organization=operator.organization)
    client = authenticated_client(operator)

    _receive(client, warehouse, [{"product_id": str(product.id), "quantity": 10}])
    _receive(client, warehouse, [{"product_id": str(product.id), "quantity": 5}])

    item = StockItem.objects.get(product=product, warehouse=warehouse)
    assert item.on_hand == 15
    afters = list(item.movements.order_by("created_at").values_list("on_hand_after", flat=True))
    assert afters == [10, 15]


def test_receipt_is_all_or_nothing(operator: User, warehouse: Warehouse) -> None:
    valid = make_product(organization=operator.organization)
    inactive = make_product(organization=operator.organization, is_active=False)

    response = _receive(
        authenticated_client(operator),
        warehouse,
        [
            {"product_id": str(valid.id), "quantity": 10},
            {"product_id": str(inactive.id), "quantity": 1},
        ],
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PRODUCT_NOT_AVAILABLE"
    assert not StockReceipt.objects.exists()
    assert not StockMovement.objects.exists()
    assert not StockItem.objects.filter(on_hand__gt=0).exists()


def test_products_and_warehouses_of_other_organizations_are_rejected(
    operator: User, warehouse: Warehouse
) -> None:
    foreign_product = make_product()
    client = authenticated_client(operator)

    product_response = _receive(
        client, warehouse, [{"product_id": str(foreign_product.id), "quantity": 1}]
    )
    warehouse_response = _receive(
        client,
        make_warehouse(),
        [{"product_id": str(make_product(organization=operator.organization).id), "quantity": 1}],
    )

    assert product_response.json()["error"]["code"] == "PRODUCT_NOT_AVAILABLE"
    assert warehouse_response.json()["error"]["code"] == "WAREHOUSE_NOT_FOUND"


def test_inactive_warehouse_does_not_receive(operator: User) -> None:
    closed = make_warehouse(organization=operator.organization, is_active=False)
    product = make_product(organization=operator.organization)

    response = _receive(
        authenticated_client(operator), closed, [{"product_id": str(product.id), "quantity": 1}]
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "WAREHOUSE_INACTIVE"


def test_same_document_from_same_supplier_is_received_only_once(
    operator: User, warehouse: Warehouse
) -> None:
    supplier = make_supplier(organization=operator.organization)
    other_supplier = make_supplier(organization=operator.organization)
    product = make_product(organization=operator.organization)
    client = authenticated_client(operator)
    line = [{"product_id": str(product.id), "quantity": 3}]

    first = _receive(client, warehouse, line, supplier_id=str(supplier.id), document_number="NF-9")
    repeated = _receive(
        client, warehouse, line, supplier_id=str(supplier.id), document_number="NF-9"
    )
    other = _receive(
        client, warehouse, line, supplier_id=str(other_supplier.id), document_number="NF-9"
    )
    no_supplier_1 = _receive(client, warehouse, line, document_number="AVULSO-1")
    no_supplier_2 = _receive(client, warehouse, line, document_number="AVULSO-1")

    assert first.status_code == 201
    assert repeated.status_code == 409
    assert repeated.json()["error"]["code"] == "RECEIPT_ALREADY_REGISTERED"
    assert other.status_code == 201
    assert (no_supplier_1.status_code, no_supplier_2.status_code) == (201, 409)
    assert StockItem.objects.get(product=product).on_hand == 9  # repetidos não somaram


def test_inactive_supplier_is_rejected(operator: User, warehouse: Warehouse) -> None:
    supplier = make_supplier(organization=operator.organization, is_active=False)
    product = make_product(organization=operator.organization)

    response = _receive(
        authenticated_client(operator),
        warehouse,
        [{"product_id": str(product.id), "quantity": 1}],
        supplier_id=str(supplier.id),
    )

    assert response.json()["error"]["code"] == "SUPPLIER_NOT_AVAILABLE"


@pytest.mark.parametrize(
    "lines",
    [
        [],
        [{"product_id": "p", "quantity": 1}],
        "duplicate",
        "zero",
    ],
)
def test_invalid_lines_are_rejected(operator: User, warehouse: Warehouse, lines: Any) -> None:
    product = make_product(organization=operator.organization)
    if lines == "duplicate":
        lines = [{"product_id": str(product.id), "quantity": 1}] * 2
    elif lines == "zero":
        lines = [{"product_id": str(product.id), "quantity": 0}]

    response = _receive(authenticated_client(operator), warehouse, lines)

    assert response.status_code == 400
    assert "lines" in response.json()["error"]["details"]["fields"]


@pytest.mark.parametrize(
    ("role", "allowed"),
    [
        (Role.ADMIN, True),
        (Role.MANAGER, True),
        (Role.WAREHOUSE, True),
        (Role.SALES, False),
        (Role.VIEWER, False),
    ],
)
def test_receiving_requires_inventory_update(role: Role, allowed: bool) -> None:
    user = make_user(role=role)
    warehouse = make_warehouse(organization=user.organization)
    product = make_product(organization=user.organization)

    response = _receive(
        authenticated_client(user), warehouse, [{"product_id": str(product.id), "quantity": 1}]
    )

    assert response.status_code == (201 if allowed else 403)
