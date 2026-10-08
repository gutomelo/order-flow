import pytest

from apps.catalog.tests.factories import make_product
from apps.identity.domain.permissions import Role
from apps.identity.tests.factories import authenticated_client, make_user
from apps.inventory.tests.factories import make_stock_item, make_warehouse

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

URL = "/api/v1/inventory/availability"


def test_reports_balances_and_zero_for_products_without_stock() -> None:
    user = make_user(role=Role.SALES)
    warehouse = make_warehouse(organization=user.organization)
    stocked = make_stock_item(warehouse=warehouse, on_hand=10, reserved=3)
    never_stocked = make_product(organization=user.organization)

    response = authenticated_client(user).get(
        URL,
        {"warehouse": str(warehouse.id), "products": f"{stocked.product_id},{never_stocked.id}"},
    )

    assert response.status_code == 200
    assert sorted(response.json(), key=lambda r: r["available"], reverse=True) == [
        {"product_id": str(stocked.product_id), "on_hand": 10, "reserved": 3, "available": 7},
        {"product_id": str(never_stocked.id), "on_hand": 0, "reserved": 0, "available": 0},
    ]


def test_stock_of_another_organization_is_never_revealed() -> None:
    user = make_user(role=Role.SALES)
    foreign = make_stock_item(on_hand=50)

    response = authenticated_client(user).get(
        URL, {"warehouse": str(foreign.warehouse_id), "products": str(foreign.product_id)}
    )

    assert response.json()[0]["available"] == 0


@pytest.mark.parametrize("query", [{}, {"warehouse": "x", "products": "y"}])
def test_requires_valid_ids(query: dict[str, str]) -> None:
    response = authenticated_client(make_user(role=Role.SALES)).get(URL, query)

    assert response.status_code == 400


def test_requires_inventory_read() -> None:
    finance = make_user(role=Role.FINANCE)  # sem inventory:read na matriz

    response = authenticated_client(finance).get(URL, {"warehouse": "x", "products": "y"})

    assert response.status_code == 403
