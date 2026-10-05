from typing import Any

import pytest

from apps.customers.tests.factories import make_address, make_customer
from apps.identity.domain.permissions import Role
from apps.identity.tests.factories import authenticated_client, make_user
from apps.orders.tests.factories import ORDERS, Scenario, make_scenario

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def s() -> Scenario:
    return make_scenario()


def test_cancels_with_a_reason_once(s: Scenario) -> None:
    order_id = s.place().json()["id"]

    first = s.client.post(f"{ORDERS}/{order_id}/cancel", {"reason": "Cliente desistiu"})
    again = s.client.post(f"{ORDERS}/{order_id}/cancel", {"reason": "De novo"})

    assert first.json()["status"] == "CANCELLED"
    assert first.json()["history"][-1]["reason"] == "Cliente desistiu"
    assert again.status_code == 200
    assert len(again.json()["history"]) == 2  # sem nova transição


def test_cancellation_requires_a_reason(s: Scenario) -> None:
    order_id = s.place().json()["id"]

    response = s.client.post(f"{ORDERS}/{order_id}/cancel", {"reason": "  "})

    assert response.json()["error"] == {
        "code": "CANCEL_REASON_REQUIRED",
        "message": "Informe o motivo do cancelamento.",
        "details": {"field": "reason"},
    }


def test_quote_uses_the_same_rules_as_the_order(s: Scenario) -> None:
    response = s.client.post(
        f"{ORDERS}/quote",
        {"customer_id": str(s.customer.id), "lines": s.payload()["lines"]},
        format="json",
    )

    assert response.status_code == 200
    body = response.json()
    assert [(line["sku"], line["line_total"]) for line in body["lines"]] == [
        ("COLA", "7.00"),
        ("AGUA", "6.00"),
    ]
    assert (body["total"], body["currency"]) == ("13.00", "BRL")


def test_quote_points_to_the_lines_without_price(s: Scenario) -> None:
    s.price_list.items.filter(product=s.water).delete()

    response = s.client.post(
        f"{ORDERS}/quote",
        {"customer_id": str(s.customer.id), "lines": s.payload()["lines"]},
        format="json",
    )

    assert response.json()["error"]["details"] == {"product_ids": [str(s.water.id)]}


def test_list_filters_by_status_and_searches_number_customer_and_po(s: Scenario) -> None:
    acme = make_customer(organization=s.user.organization, legal_name="Acme Comércio")
    make_address(acme, is_default_shipping=True)
    s.place()  # nº 1
    s.place(s.payload(customer_id=str(acme.id), purchase_order_number="PO-778"))  # nº 2
    s.draft()

    def numbers(query: str) -> list[Any]:
        return [o["number"] for o in s.client.get(f"{ORDERS}?{query}").json()["results"]]

    assert numbers("status=DRAFT") == [None]
    assert sorted(numbers("status=PENDING")) == [1, 2]
    assert numbers("search=acme") == [2]
    assert numbers("search=PO-778") == [2]
    assert numbers(f"customer={acme.id}") == [2]


def test_orders_of_another_organization_are_not_found(s: Scenario) -> None:
    foreign_id = make_scenario().place().json()["id"]

    assert s.client.get(f"{ORDERS}/{foreign_id}").status_code == 404
    patched = s.client.patch(f"{ORDERS}/{foreign_id}", {"notes": "x"}, format="json")
    assert patched.status_code == 404
    assert s.client.post(f"{ORDERS}/{foreign_id}/submit").status_code == 404
    assert s.client.post(f"{ORDERS}/{foreign_id}/cancel", {"reason": "x"}).status_code == 404


def test_cannot_order_for_a_customer_of_another_organization(s: Scenario) -> None:
    foreign_customer = make_scenario().customer

    response = s.place(s.payload(customer_id=str(foreign_customer.id)))

    assert response.json()["error"]["code"] == "CUSTOMER_INACTIVE"


@pytest.mark.parametrize(
    ("role", "read", "create", "cancel"),
    [
        (Role.ADMIN, 200, 201, 200),
        (Role.MANAGER, 200, 201, 200),
        (Role.SALES, 200, 201, 200),
        (Role.WAREHOUSE, 200, 403, 403),
        (Role.FINANCE, 200, 403, 403),
        (Role.VIEWER, 200, 403, 403),
    ],
)
def test_permission_matrix(role: Role, read: int, create: int, cancel: int) -> None:
    s = make_scenario()
    order_id = s.place().json()["id"]
    user = make_user(role=role, organization=s.user.organization)
    client = authenticated_client(user)

    assert client.get(ORDERS).status_code == read
    assert client.post(f"{ORDERS}/drafts", s.payload(), format="json").status_code == create
    assert client.post(f"{ORDERS}/{order_id}/cancel", {"reason": "x"}).status_code == cancel
