import pytest
from pytest_django import DjangoAssertNumQueries

from apps.catalog.tests.factories import make_product
from apps.identity.domain.permissions import Role
from apps.identity.models import User
from apps.identity.tests.factories import authenticated_client, make_user
from apps.inventory.tests.factories import make_stock_item, make_warehouse

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def manager() -> User:
    return make_user(role=Role.MANAGER)


# ---------------------------------------------------------------------------
# Depósitos
# ---------------------------------------------------------------------------


def test_creates_warehouse_with_normalized_unique_code(manager: User) -> None:
    client = authenticated_client(manager)

    created = client.post("/api/v1/inventory/warehouses", {"code": "cd-sp", "name": "CD São Paulo"})
    duplicated = client.post("/api/v1/inventory/warehouses", {"code": "CD-SP", "name": "Outro"})
    invalid = client.post("/api/v1/inventory/warehouses", {"code": "C D", "name": "X"})

    assert created.json()["code"] == "CD-SP"
    assert duplicated.json()["error"]["code"] == "WAREHOUSE_CODE_ALREADY_IN_USE"
    assert invalid.json()["error"]["code"] == "INVALID_WAREHOUSE_CODE"


def test_warehouse_with_stock_cannot_be_deactivated(manager: User) -> None:
    warehouse = make_warehouse(organization=manager.organization)
    item = make_stock_item(warehouse=warehouse, on_hand=1)
    client = authenticated_client(manager)

    blocked = client.post(f"/api/v1/inventory/warehouses/{warehouse.id}/deactivate")
    item.on_hand = 0
    item.save()
    allowed = client.post(f"/api/v1/inventory/warehouses/{warehouse.id}/deactivate")

    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "WAREHOUSE_HAS_STOCK"
    assert allowed.json()["is_active"] is False


def test_warehouses_are_scoped_to_the_organization(manager: User) -> None:
    mine = make_warehouse(organization=manager.organization)
    foreign = make_warehouse()
    client = authenticated_client(manager)

    assert [w["id"] for w in client.get("/api/v1/inventory/warehouses").json()] == [str(mine.id)]
    assert (
        client.patch(f"/api/v1/inventory/warehouses/{foreign.id}", {"name": "X"}).status_code == 404
    )


# ---------------------------------------------------------------------------
# Saldos
# ---------------------------------------------------------------------------


def test_low_stock_filter_uses_available_against_reorder_point(manager: User) -> None:
    warehouse = make_warehouse(organization=manager.organization)
    low = make_stock_item(warehouse=warehouse, on_hand=10, reserved=6, reorder_point=5)  # 4 <= 5
    make_stock_item(warehouse=warehouse, on_hand=10, reorder_point=5)  # 10 > 5
    make_stock_item(warehouse=warehouse, on_hand=0)  # sem ponto de reposição

    response = authenticated_client(manager).get(
        "/api/v1/inventory/stock-items", {"low_stock": "true"}
    )

    results = response.json()["results"]
    assert [r["id"] for r in results] == [str(low.id)]
    assert results[0]["is_low_stock"] is True


def test_stock_search_by_sku_and_warehouse_filter(manager: User) -> None:
    sp = make_warehouse(organization=manager.organization)
    rj = make_warehouse(organization=manager.organization)
    coffee = make_product(organization=manager.organization, sku="CAFE-500")
    make_stock_item(warehouse=sp, product=coffee, on_hand=1)
    make_stock_item(warehouse=rj, product=coffee, on_hand=2)
    make_stock_item(warehouse=sp, on_hand=3)
    client = authenticated_client(manager)

    by_sku = client.get("/api/v1/inventory/stock-items", {"search": "cafe"}).json()["results"]
    by_warehouse = client.get("/api/v1/inventory/stock-items", {"warehouse": str(rj.id)}).json()[
        "results"
    ]

    assert len(by_sku) == 2
    assert [r["on_hand"] for r in by_warehouse] == [2]


def test_reorder_point_can_be_configured_without_touching_the_balance(manager: User) -> None:
    item = make_stock_item(warehouse=make_warehouse(organization=manager.organization), on_hand=3)

    response = authenticated_client(manager).patch(
        f"/api/v1/inventory/stock-items/{item.id}", {"reorder_point": 5}
    )

    assert response.json()["reorder_point"] == 5
    assert response.json()["is_low_stock"] is True
    assert not item.movements.exists()


def test_stock_of_other_organizations_is_invisible(manager: User) -> None:
    foreign = make_stock_item(on_hand=5)
    client = authenticated_client(manager)

    assert client.get("/api/v1/inventory/stock-items").json()["count"] == 0
    assert client.get(f"/api/v1/inventory/stock-items/{foreign.id}").status_code == 404


# ---------------------------------------------------------------------------
# Movimentações
# ---------------------------------------------------------------------------


def _receive(user: User, warehouse_id: str, product_id: str, quantity: int) -> None:
    response = authenticated_client(user).post(
        "/api/v1/inventory/receipts",
        {"warehouse_id": warehouse_id, "lines": [{"product_id": product_id, "quantity": quantity}]},
        format="json",
    )
    assert response.status_code == 201


def test_movements_are_listed_newest_first_with_filters(manager: User) -> None:
    warehouse = make_warehouse(organization=manager.organization)
    coffee = make_product(organization=manager.organization, sku="CAFE")
    sugar = make_product(organization=manager.organization, sku="ACUCAR")
    _receive(manager, str(warehouse.id), str(coffee.id), 5)
    _receive(manager, str(warehouse.id), str(sugar.id), 7)
    client = authenticated_client(manager)

    everything = client.get("/api/v1/inventory/movements").json()["results"]
    by_product = client.get("/api/v1/inventory/movements", {"product": str(coffee.id)}).json()
    by_type = client.get("/api/v1/inventory/movements", {"type": "ADJUSTMENT"}).json()
    future = client.get(
        "/api/v1/inventory/movements", {"created_after": "2999-01-01T00:00:00Z"}
    ).json()

    assert [m["product"]["sku"] for m in everything] == ["ACUCAR", "CAFE"]
    assert everything[0]["performed_by"]["id"] == str(manager.id)
    assert by_product["count"] == 1
    assert by_type["count"] == 0
    assert future["count"] == 0


def test_naive_datetime_filter_is_rejected(manager: User) -> None:
    response = authenticated_client(manager).get(
        "/api/v1/inventory/movements", {"created_after": "2026-10-01T00:00:00"}
    )

    assert response.status_code == 400


def test_movement_listing_does_not_grow_queries_with_results(
    manager: User, django_assert_max_num_queries: DjangoAssertNumQueries
) -> None:
    warehouse = make_warehouse(organization=manager.organization)
    for _ in range(10):
        _receive(
            manager, str(warehouse.id), str(make_product(organization=manager.organization).id), 1
        )
    client = authenticated_client(manager)

    with django_assert_max_num_queries(6):
        response = client.get("/api/v1/inventory/movements")

    assert response.json()["count"] == 10


@pytest.mark.parametrize(
    ("role", "can_read"),
    [(Role.SALES, True), (Role.VIEWER, True), (Role.WAREHOUSE, True), (Role.FINANCE, False)],
)
def test_reading_inventory_follows_the_rbac_matrix(role: Role, can_read: bool) -> None:
    client = authenticated_client(make_user(role=role))

    for path in ("stock-items", "movements", "warehouses"):
        assert (client.get(f"/api/v1/inventory/{path}").status_code == 200) is can_read
