from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.customers.models import Customer, CustomerAddress, CustomerContact
from apps.customers.tests.factories import make_address, make_contact, make_customer
from apps.identity.domain.permissions import Role
from apps.identity.models import User
from apps.identity.tests.factories import authenticated_client, make_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

ADDRESS: dict[str, Any] = {
    "label": "Matriz",
    "postal_code": "01310-100",
    "street": "Avenida Paulista",
    "number": "1000",
    "district": "Bela Vista",
    "city": "São Paulo",
    "state": "SP",
}


@pytest.fixture
def seller() -> User:
    return make_user(role=Role.SALES)


@pytest.fixture
def customer(seller: User) -> Customer:
    return make_customer(organization=seller.organization)


@pytest.fixture
def client(seller: User) -> APIClient:
    return authenticated_client(seller)


def _addresses(customer: Customer) -> str:
    return f"/api/v1/customers/{customer.id}/addresses"


def _contacts(customer: Customer) -> str:
    return f"/api/v1/customers/{customer.id}/contacts"


def _roles(customer: Customer) -> dict[str, tuple[bool, bool]]:
    return {
        a.label: (a.is_billing, a.is_default_shipping)
        for a in CustomerAddress.objects.filter(customer=customer)
    }


# Endereços ------------------------------------------------------------------------------------


def test_first_address_takes_both_roles_and_the_next_takes_none(
    client: APIClient, customer: Customer
) -> None:
    first = client.post(_addresses(customer), ADDRESS)
    second = client.post(_addresses(customer), {**ADDRESS, "label": "Filial Campinas"})

    assert first.status_code == 201
    assert first.json()["postal_code"] == "01310100"
    assert (first.json()["is_billing"], first.json()["is_default_shipping"]) == (True, True)
    assert (second.json()["is_billing"], second.json()["is_default_shipping"]) == (False, False)


def test_moving_a_role_keeps_exactly_one_holder(client: APIClient, customer: Customer) -> None:
    make_address(customer, label="Matriz", is_billing=True, is_default_shipping=True)
    branch = make_address(customer, label="Filial")

    response = client.post(f"{_addresses(customer)}/{branch.id}/set-default-shipping")

    assert response.status_code == 200
    assert response.json()["is_default_shipping"] is True
    assert _roles(customer) == {"Matriz": (True, False), "Filial": (False, True)}


def test_removing_a_role_holder_promotes_the_oldest_remaining_address(
    client: APIClient, customer: Customer
) -> None:
    main = make_address(customer, label="Matriz", is_billing=True, is_default_shipping=True)
    make_address(customer, label="Filial A")
    make_address(customer, label="Filial B")

    response = client.delete(f"{_addresses(customer)}/{main.id}")

    assert response.status_code == 204
    assert _roles(customer) == {"Filial A": (True, True), "Filial B": (False, False)}


def test_rejects_invalid_postal_code_and_state(client: APIClient, customer: Customer) -> None:
    bad_postal_code = client.post(_addresses(customer), {**ADDRESS, "postal_code": "0131-01"})
    bad_state = client.post(_addresses(customer), {**ADDRESS, "state": "XX"})

    assert bad_postal_code.status_code == 422
    assert bad_postal_code.json()["error"]["code"] == "INVALID_POSTAL_CODE"
    assert bad_postal_code.json()["error"]["details"] == {"field": "postal_code"}
    assert bad_state.status_code == 400
    assert bad_state.json()["error"]["code"] == "VALIDATION_ERROR"


def test_updates_address_fields_without_touching_roles(
    client: APIClient, customer: Customer
) -> None:
    address = make_address(customer, is_billing=True, is_default_shipping=True)

    response = client.patch(
        f"{_addresses(customer)}/{address.id}", {"number": "1500", "postal_code": "01311-000"}
    )

    assert response.status_code == 200
    assert (response.json()["number"], response.json()["postal_code"]) == ("1500", "01311000")
    assert response.json()["is_billing"] is True


def test_address_of_another_customer_is_not_found(client: APIClient, seller: User) -> None:
    """Anti-IDOR: o ID existe, mas não pertence ao cliente da URL."""
    mine = make_customer(organization=seller.organization)
    other_customer = make_customer(organization=seller.organization)
    other_address = make_address(other_customer)
    url = f"{_addresses(mine)}/{other_address.id}"

    assert client.patch(url, {"label": "Hack"}).status_code == 404
    assert client.delete(url).status_code == 404
    assert client.post(f"{url}/set-billing").status_code == 404
    assert CustomerAddress.objects.filter(id=other_address.id, label="Matriz").exists()


def test_addresses_of_another_organization_are_not_found(client: APIClient) -> None:
    foreign = make_customer()
    make_address(foreign)

    assert client.get(_addresses(foreign)).status_code == 404
    assert client.post(_addresses(foreign), ADDRESS).status_code == 404


def test_malformed_customer_id_is_not_found(client: APIClient) -> None:
    assert client.get("/api/v1/customers/not-a-uuid/addresses").status_code == 404


# Contatos -------------------------------------------------------------------------------------


def test_first_contact_is_primary_and_primary_can_be_moved(
    client: APIClient, customer: Customer
) -> None:
    first = client.post(_contacts(customer), {"name": "Ana Lima", "email": "ana@example.com"})
    second = client.post(_contacts(customer), {"name": "Rui Costa", "phone": "11 99999-0000"})

    moved = client.post(f"{_contacts(customer)}/{second.json()['id']}/set-primary")

    assert first.json()["is_primary"] is True
    assert second.json()["is_primary"] is False
    assert moved.json()["is_primary"] is True
    primaries = CustomerContact.objects.filter(customer=customer, is_primary=True)
    assert [c.name for c in primaries] == ["Rui Costa"]


def test_contact_needs_an_email_or_a_phone(client: APIClient, customer: Customer) -> None:
    contact = make_contact(customer, email="ana@example.com", phone="")

    created = client.post(_contacts(customer), {"name": "Sem canal"})
    emptied = client.patch(f"{_contacts(customer)}/{contact.id}", {"email": ""})

    for response in (created, emptied):
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "CONTACT_CHANNEL_REQUIRED"
        assert response.json()["error"]["details"] == {"field": "email"}


def test_removing_the_primary_contact_promotes_the_oldest_remaining(
    client: APIClient, customer: Customer
) -> None:
    primary = make_contact(customer, name="Ana", is_primary=True)
    make_contact(customer, name="Bia")
    make_contact(customer, name="Caio")

    client.delete(f"{_contacts(customer)}/{primary.id}")

    primaries = CustomerContact.objects.filter(customer=customer, is_primary=True)
    assert [c.name for c in primaries] == ["Bia"]


def test_lists_contacts_of_the_customer_only(client: APIClient, customer: Customer) -> None:
    make_contact(customer, name="Ana", is_primary=True)
    make_contact(make_customer(organization=customer.organization), name="De outro cliente")

    response = client.get(_contacts(customer))

    assert [c["name"] for c in response.json()] == ["Ana"]


@pytest.mark.parametrize(
    ("role", "read", "write"),
    [
        (Role.SALES, 200, 201),
        (Role.FINANCE, 200, 403),
        (Role.VIEWER, 200, 403),
        (Role.WAREHOUSE, 403, 403),
    ],
)
def test_permission_matrix(role: Role, read: int, write: int) -> None:
    user = make_user(role=role)
    customer = make_customer(organization=user.organization)
    client = authenticated_client(user)

    assert client.get(_addresses(customer)).status_code == read
    assert client.get(_contacts(customer)).status_code == read
    assert client.post(_addresses(customer), ADDRESS).status_code == write
    assert client.post(_contacts(customer), {"name": "A", "email": "a@x.com"}).status_code == write
