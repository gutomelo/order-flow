from typing import Any

import pytest
from pytest_django import DjangoAssertNumQueries

from apps.catalog.models import Product
from apps.catalog.tests.factories import make_category, make_product
from apps.identity.domain.permissions import Role
from apps.identity.models import User
from apps.identity.tests.factories import authenticated_client, make_user
from apps.suppliers.tests.factories import make_supplier

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def manager() -> User:
    return make_user(role=Role.MANAGER)


def _payload(**overrides: Any) -> dict[str, Any]:
    return {"sku": "bev-coke-350", "name": "Refrigerante Cola 350ml", **overrides}


def test_creates_product_with_normalized_sku_category_and_supplier(manager: User) -> None:
    drinks = make_category(organization=manager.organization, name="Bebidas")
    sodas = make_category(parent=drinks, name="Refrigerantes")
    supplier = make_supplier(organization=manager.organization, trade_name="Sul Express")

    response = authenticated_client(manager).post(
        "/api/v1/products",
        _payload(
            category_id=str(sodas.id),
            default_supplier_id=str(supplier.id),
            barcode="7891000315507",
            unit="BOX",
        ),
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["sku"] == "BEV-COKE-350"
    assert body["category"]["path"] == "Bebidas › Refrigerantes"  # noqa: RUF001
    assert body["default_supplier"]["display_name"] == "Sul Express"
    assert "price" not in body  # preço é do módulo pricing


def test_sku_is_unique_per_organization_ignoring_case(manager: User) -> None:
    make_product(organization=manager.organization, sku="BEV-1")
    make_product(sku="BEV-2")  # outra organização

    duplicated = authenticated_client(manager).post("/api/v1/products", _payload(sku="bev-1"))
    other_org_sku = authenticated_client(manager).post("/api/v1/products", _payload(sku="BEV-2"))

    assert duplicated.status_code == 409
    assert duplicated.json()["error"]["code"] == "SKU_ALREADY_IN_USE"
    assert other_org_sku.status_code == 201


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"sku": "com espaço"}, "INVALID_SKU"),
        ({"sku": "-COMECA-COM-HIFEN"}, "INVALID_SKU"),
        ({"barcode": "4006381333932"}, "INVALID_BARCODE"),
    ],
)
def test_rejects_invalid_identifiers(manager: User, payload: dict[str, str], code: str) -> None:
    response = authenticated_client(manager).post("/api/v1/products", _payload(**payload))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == code


def test_barcode_is_unique_per_organization_when_present(manager: User) -> None:
    make_product(organization=manager.organization, barcode="4006381333931")
    make_product(organization=manager.organization)  # sem código: vários permitidos
    client = authenticated_client(manager)

    duplicated = client.post("/api/v1/products", _payload(sku="X1", barcode="4006381333931"))
    without_barcode = client.post("/api/v1/products", _payload(sku="X2"))

    assert duplicated.status_code == 409
    assert duplicated.json()["error"]["code"] == "BARCODE_ALREADY_IN_USE"
    assert without_barcode.status_code == 201


@pytest.mark.parametrize("scenario", ["inactive", "other_organization"])
def test_category_must_be_active_and_of_the_same_organization(manager: User, scenario: str) -> None:
    category = (
        make_category(organization=manager.organization, is_active=False)
        if scenario == "inactive"
        else make_category()
    )

    response = authenticated_client(manager).post(
        "/api/v1/products", _payload(category_id=str(category.id))
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CATEGORY_NOT_AVAILABLE"


@pytest.mark.parametrize("scenario", ["inactive", "other_organization"])
def test_supplier_must_be_active_and_of_the_same_organization(manager: User, scenario: str) -> None:
    supplier = (
        make_supplier(organization=manager.organization, is_active=False)
        if scenario == "inactive"
        else make_supplier()
    )

    response = authenticated_client(manager).post(
        "/api/v1/products", _payload(default_supplier_id=str(supplier.id))
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SUPPLIER_NOT_AVAILABLE"


def test_sku_cannot_be_changed(manager: User) -> None:
    product = make_product(organization=manager.organization, sku="ORIGINAL")

    response = authenticated_client(manager).patch(
        f"/api/v1/products/{product.id}", {"sku": "NOVO", "name": "Novo nome"}
    )

    assert response.status_code == 200
    product.refresh_from_db()
    assert (product.sku, product.name) == ("ORIGINAL", "Novo nome")


def test_patch_can_clear_category(manager: User) -> None:
    category = make_category(organization=manager.organization)
    product = make_product(organization=manager.organization, category=category)

    response = authenticated_client(manager).patch(
        f"/api/v1/products/{product.id}", {"category_id": None}, format="json"
    )

    assert response.json()["category"] is None


def test_category_filter_includes_subcategories(manager: User) -> None:
    drinks = make_category(organization=manager.organization, name="Bebidas")
    sodas = make_category(parent=drinks, name="Refrigerantes")
    cans = make_category(parent=sodas, name="Lata")
    make_product(organization=manager.organization, name="A", category=drinks)
    make_product(organization=manager.organization, name="B", category=cans)
    make_product(organization=manager.organization, name="C")

    response = authenticated_client(manager).get("/api/v1/products", {"category": str(drinks.id)})

    assert [p["name"] for p in response.json()["results"]] == ["A", "B"]


def test_search_and_status_filters(manager: User) -> None:
    make_product(organization=manager.organization, sku="CAFE-500", name="Café 500g")
    make_product(organization=manager.organization, name="Açúcar", is_active=False)
    client = authenticated_client(manager)

    by_sku = client.get("/api/v1/products", {"search": "cafe-5"}).json()["results"]
    inactive = client.get("/api/v1/products", {"is_active": "false"}).json()["results"]

    assert [p["sku"] for p in by_sku] == ["CAFE-500"]
    assert [p["name"] for p in inactive] == ["Açúcar"]


def test_invalid_category_filter_is_a_validation_error(manager: User) -> None:
    response = authenticated_client(manager).get("/api/v1/products", {"category": "abc"})

    assert response.status_code == 400
    assert "category" in response.json()["error"]["details"]["fields"]


def test_listing_does_not_issue_one_query_per_product(
    manager: User, django_assert_max_num_queries: DjangoAssertNumQueries
) -> None:
    root = make_category(organization=manager.organization)
    leaf = make_category(parent=make_category(parent=root))
    supplier = make_supplier(organization=manager.organization)
    for _ in range(15):
        make_product(organization=manager.organization, category=leaf, default_supplier=supplier)
    client = authenticated_client(manager)

    # autenticação (usuário + organização) + contagem + página — independe do nº de produtos.
    with django_assert_max_num_queries(6):
        response = client.get("/api/v1/products")

    assert response.json()["count"] == 15


def test_products_of_other_organizations_are_invisible(manager: User) -> None:
    foreign = make_product()
    client = authenticated_client(manager)

    assert client.get("/api/v1/products").json()["count"] == 0
    assert client.get(f"/api/v1/products/{foreign.id}").status_code == 404
    assert client.post(f"/api/v1/products/{foreign.id}/deactivate").status_code == 404
    foreign.refresh_from_db()
    assert foreign.is_active is True


def test_deactivated_product_stays_referenceable(manager: User) -> None:
    product = make_product(organization=manager.organization)

    response = authenticated_client(manager).post(f"/api/v1/products/{product.id}/deactivate")

    assert response.json()["is_active"] is False
    assert Product.objects.filter(id=product.id).exists()


@pytest.mark.parametrize("role", list(Role))
def test_every_role_reads_the_catalog_but_only_managers_change_it(role: Role) -> None:
    client = authenticated_client(make_user(role=role))

    assert client.get("/api/v1/products").status_code == 200
    expected = 201 if role in {Role.ADMIN, Role.MANAGER} else 403
    assert client.post("/api/v1/products", _payload()).status_code == expected
