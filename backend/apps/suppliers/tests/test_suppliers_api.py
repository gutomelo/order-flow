import pytest

from apps.identity.domain.permissions import Role
from apps.identity.models import User
from apps.identity.tests.factories import authenticated_client, make_user
from apps.suppliers.models import Supplier
from apps.suppliers.tests.factories import generate_cnpj, make_supplier

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def manager() -> User:
    return make_user(role=Role.MANAGER)


def test_creates_supplier_with_alphanumeric_cnpj(manager: User) -> None:
    response = authenticated_client(manager).post(
        "/api/v1/suppliers",
        {"legal_name": "Distribuidora Sul Ltda", "tax_id": "12.abc.345/01de-35"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["tax_id"] == "12ABC34501DE35"
    assert body["tax_id_formatted"] == "12.ABC.345/01DE-35"
    assert Supplier.objects.get(id=body["id"]).organization_id == manager.organization_id


def test_rejects_invalid_cnpj(manager: User) -> None:
    response = authenticated_client(manager).post(
        "/api/v1/suppliers", {"legal_name": "X", "tax_id": "11.222.333/0001-82"}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_TAX_ID"


def test_cnpj_is_unique_per_organization_regardless_of_mask(manager: User) -> None:
    make_supplier(organization=manager.organization, tax_id="11222333000181")
    make_supplier(tax_id="12ABC34501DE35")  # outra organização

    duplicated = authenticated_client(manager).post(
        "/api/v1/suppliers", {"legal_name": "X", "tax_id": "11.222.333/0001-81"}
    )
    same_as_other_org = authenticated_client(manager).post(
        "/api/v1/suppliers", {"legal_name": "Y", "tax_id": "12ABC34501DE35"}
    )

    assert duplicated.status_code == 409
    assert duplicated.json()["error"]["code"] == "TAX_ID_ALREADY_IN_USE"
    assert same_as_other_org.status_code == 201


def test_list_is_scoped_searchable_and_filterable(manager: User) -> None:
    make_supplier(organization=manager.organization, legal_name="Alfa Embalagens")
    make_supplier(organization=manager.organization, legal_name="Beta Bebidas", is_active=False)
    make_supplier(legal_name="Alfa de Outra Empresa")
    client = authenticated_client(manager)

    search = client.get("/api/v1/suppliers", {"search": "alfa"}).json()["results"]
    inactive = client.get("/api/v1/suppliers", {"is_active": "false"}).json()["results"]

    assert [s["legal_name"] for s in search] == ["Alfa Embalagens"]
    assert [s["legal_name"] for s in inactive] == ["Beta Bebidas"]


def test_supplier_of_another_organization_is_not_found(manager: User) -> None:
    foreign = make_supplier()
    client = authenticated_client(manager)

    assert client.get(f"/api/v1/suppliers/{foreign.id}").status_code == 404
    assert client.patch(f"/api/v1/suppliers/{foreign.id}", {"legal_name": "X"}).status_code == 404
    assert client.post(f"/api/v1/suppliers/{foreign.id}/deactivate").status_code == 404


def test_update_and_deactivate(manager: User) -> None:
    supplier = make_supplier(organization=manager.organization)
    client = authenticated_client(manager)

    updated = client.patch(f"/api/v1/suppliers/{supplier.id}", {"trade_name": "Sul Express"})
    deactivated = client.post(f"/api/v1/suppliers/{supplier.id}/deactivate")

    assert updated.json()["display_name"] == "Sul Express"
    assert deactivated.json()["is_active"] is False


@pytest.mark.parametrize(
    ("role", "can_read", "can_write"),
    [
        (Role.ADMIN, True, True),
        (Role.MANAGER, True, True),
        (Role.WAREHOUSE, True, False),
        (Role.FINANCE, True, False),
        (Role.VIEWER, True, False),
        (Role.SALES, False, False),
    ],
)
def test_permissions_follow_the_rbac_matrix(role: Role, can_read: bool, can_write: bool) -> None:
    client = authenticated_client(make_user(role=role))

    read = client.get("/api/v1/suppliers")
    write = client.post("/api/v1/suppliers", {"legal_name": "X", "tax_id": generate_cnpj()})

    assert (read.status_code == 200) is can_read
    assert (write.status_code == 201) is can_write
    if not can_write:
        assert write.status_code == 403
