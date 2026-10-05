import pytest

from apps.customers.models import Customer
from apps.customers.tests.factories import make_customer, make_segment
from apps.identity.domain.permissions import Role
from apps.identity.models import User
from apps.identity.tests.factories import authenticated_client, make_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

URL = "/api/v1/customers"


@pytest.fixture
def seller() -> User:
    return make_user(role=Role.SALES)


def test_seller_creates_customer_in_an_active_segment(seller: User) -> None:
    segment = make_segment(organization=seller.organization)

    response = authenticated_client(seller).post(
        URL,
        {
            "legal_name": "Mercado Central Ltda",
            "trade_name": "Mercado Central",
            "tax_id": "11.222.333/0001-81",
            "segment_id": str(segment.id),
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["tax_id"] == "11222333000181"
    assert body["tax_id_formatted"] == "11.222.333/0001-81"
    assert body["segment"] == {
        "id": str(segment.id),
        "code": segment.code,
        "name": segment.name,
        "is_active": True,
    }
    assert Customer.objects.get(id=body["id"]).organization_id == seller.organization_id


def test_rejects_invalid_cnpj(seller: User) -> None:
    response = authenticated_client(seller).post(
        URL, {"legal_name": "X", "tax_id": "11.222.333/0001-82"}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_TAX_ID"


def test_cnpj_is_unique_per_organization(seller: User) -> None:
    make_customer(organization=seller.organization, tax_id="11222333000181")
    make_customer(tax_id="12ABC34501DE35")  # outra organização
    client = authenticated_client(seller)

    duplicated = client.post(URL, {"legal_name": "X", "tax_id": "11.222.333/0001-81"})
    same_as_other_org = client.post(URL, {"legal_name": "Y", "tax_id": "12.ABC.345/01DE-35"})

    assert duplicated.status_code == 409
    assert duplicated.json()["error"] == {
        "code": "TAX_ID_ALREADY_IN_USE",
        "message": "Já existe um cliente com este CNPJ.",
        "details": {"field": "tax_id"},
    }
    assert same_as_other_org.status_code == 201


@pytest.mark.parametrize("scenario", ["inactive", "other_organization", "missing"])
def test_segment_must_be_an_active_segment_of_the_organization(seller: User, scenario: str) -> None:
    segment_id = {
        "inactive": lambda: make_segment(organization=seller.organization, is_active=False).id,
        "other_organization": lambda: make_segment().id,
        "missing": lambda: "8d1f1f8e-6a5c-4a8e-9a77-3f1b9b0e2c11",
    }[scenario]()

    response = authenticated_client(seller).post(
        URL, {"legal_name": "X", "tax_id": "11222333000181", "segment_id": str(segment_id)}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SEGMENT_NOT_AVAILABLE"
    assert response.json()["error"]["details"] == {"field": "segment_id"}


def test_update_changes_and_clears_the_segment(seller: User) -> None:
    customer = make_customer(
        organization=seller.organization, segment=make_segment(organization=seller.organization)
    )
    other = make_segment(organization=seller.organization)
    client = authenticated_client(seller)

    moved = client.patch(f"{URL}/{customer.id}", {"segment_id": str(other.id)})
    cleared = client.patch(f"{URL}/{customer.id}", {"segment_id": None}, format="json")

    assert moved.json()["segment"]["id"] == str(other.id)
    assert cleared.status_code == 200
    assert cleared.json()["segment"] is None


def test_customer_cannot_be_reactivated_in_an_inactive_segment(seller: User) -> None:
    segment = make_segment(organization=seller.organization, is_active=False)
    customer = make_customer(organization=seller.organization, segment=segment, is_active=False)

    response = authenticated_client(seller).post(f"{URL}/{customer.id}/activate")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SEGMENT_NOT_AVAILABLE"
    customer.refresh_from_db()
    assert customer.is_active is False


def test_list_is_scoped_searchable_and_filterable(seller: User) -> None:
    segment = make_segment(organization=seller.organization)
    make_customer(organization=seller.organization, legal_name="Alfa Atacado", segment=segment)
    make_customer(organization=seller.organization, legal_name="Beta Varejo", is_active=False)
    make_customer(legal_name="Alfa de Outra Empresa")
    client = authenticated_client(seller)

    def names(query: str) -> list[str]:
        return [c["legal_name"] for c in client.get(f"{URL}?{query}").json()["results"]]

    assert names("") == ["Alfa Atacado", "Beta Varejo"]
    assert names("search=alfa") == ["Alfa Atacado"]
    assert names("is_active=false") == ["Beta Varejo"]
    assert names(f"segment={segment.id}") == ["Alfa Atacado"]


def test_customer_of_another_organization_is_not_found(seller: User) -> None:
    foreign = make_customer()
    client = authenticated_client(seller)

    assert client.get(f"{URL}/{foreign.id}").status_code == 404
    assert client.patch(f"{URL}/{foreign.id}", {"legal_name": "Hack"}).status_code == 404
    assert client.post(f"{URL}/{foreign.id}/deactivate").status_code == 404


@pytest.mark.parametrize(
    ("role", "read", "create", "update"),
    [
        (Role.ADMIN, 200, 201, 200),
        (Role.MANAGER, 200, 201, 200),
        (Role.SALES, 200, 201, 200),
        (Role.FINANCE, 200, 403, 403),
        (Role.VIEWER, 200, 403, 403),
        (Role.WAREHOUSE, 403, 403, 403),
    ],
)
def test_permission_matrix(role: Role, read: int, create: int, update: int) -> None:
    user = make_user(role=role)
    customer = make_customer(organization=user.organization)
    client = authenticated_client(user)

    assert client.get(URL).status_code == read
    assert client.post(URL, {"legal_name": "X", "tax_id": "11222333000181"}).status_code == create
    assert client.patch(f"{URL}/{customer.id}", {"legal_name": "Y"}).status_code == update
    assert client.post(f"{URL}/{customer.id}/deactivate").status_code == update
