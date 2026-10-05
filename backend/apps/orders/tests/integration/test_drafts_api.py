from decimal import Decimal

import pytest

from apps.customers.tests.factories import make_address, make_customer
from apps.orders.tests.factories import ORDERS, Scenario, make_scenario

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def s() -> Scenario:
    return make_scenario()


def test_a_draft_needs_only_the_customer(s: Scenario) -> None:
    response = s.client.post(f"{ORDERS}/drafts", {"customer_id": str(s.customer.id)})

    assert response.status_code == 201
    body = response.json()
    assert (body["status"], body["number"], body["total"]) == ("DRAFT", None, "0.00")
    assert body["warehouse"] is None
    # Entrega padrão pré-selecionada; endereço "vivo" até a submissão.
    assert body["shipping_address_id"] == str(s.address.id)
    assert [(h["from_status"], h["to_status"]) for h in body["history"]] == [(None, "DRAFT")]


def test_draft_prices_are_an_estimate_refreshed_on_every_edit(s: Scenario) -> None:
    order_id = s.draft().json()["id"]
    s.price_list.items.filter(product=s.cola).update(unit_price=Decimal("4.00"))

    edited = s.client.patch(f"{ORDERS}/{order_id}", {"notes": "Entregar pela manhã"}, format="json")

    assert edited.status_code == 200
    assert edited.json()["total"] == "14.00"  # 2 x 4,00 + 3 x 2,00: recotado
    assert edited.json()["notes"] == "Entregar pela manhã"


def test_changing_the_customer_resets_the_address_to_the_new_default(s: Scenario) -> None:
    order_id = s.draft().json()["id"]
    other = make_customer(organization=s.user.organization)
    other_address = make_address(other, is_default_shipping=True)

    body = s.client.patch(
        f"{ORDERS}/{order_id}", {"customer_id": str(other.id)}, format="json"
    ).json()

    assert body["customer"]["id"] == str(other.id)
    assert body["shipping_address_id"] == str(other_address.id)


def test_submitting_numbers_freezes_and_copies(s: Scenario) -> None:
    order_id = s.draft().json()["id"]

    response = s.client.post(f"{ORDERS}/{order_id}/submit", {"expected_total": "13.00"})

    body = response.json()
    assert response.status_code == 200
    assert (body["status"], body["number"]) == ("PENDING", 1)
    assert body["shipping"]["address_id"] == str(s.address.id)
    assert [(h["from_status"], h["to_status"]) for h in body["history"]] == [
        (None, "DRAFT"),
        ("DRAFT", "PENDING"),
    ]


def test_drafts_do_not_consume_numbers(s: Scenario) -> None:
    draft_id = s.draft().json()["id"]
    placed = s.place().json()

    submitted = s.client.post(f"{ORDERS}/{draft_id}/submit").json()

    assert (placed["number"], submitted["number"]) == (1, 2)


def test_submission_with_a_stale_total_keeps_the_draft(s: Scenario) -> None:
    order_id = s.draft().json()["id"]
    s.price_list.items.filter(product=s.cola).update(unit_price=Decimal("4.00"))

    response = s.client.post(f"{ORDERS}/{order_id}/submit", {"expected_total": "13.00"})

    assert response.status_code == 409
    assert response.json()["error"]["details"] == {"expected": "13.00", "actual": "14.00"}
    body = s.client.get(f"{ORDERS}/{order_id}").json()
    assert (body["status"], body["number"]) == ("DRAFT", None)
    assert s.place().json()["number"] == 1  # o número não foi consumido


def test_submitting_twice_is_harmless(s: Scenario) -> None:
    order_id = s.draft().json()["id"]

    first = s.client.post(f"{ORDERS}/{order_id}/submit")
    second = s.client.post(f"{ORDERS}/{order_id}/submit")

    assert second.status_code == 200
    assert second.json()["number"] == first.json()["number"]
    assert len(second.json()["history"]) == 2


def test_submitted_orders_cannot_be_edited(s: Scenario) -> None:  # O6
    order_id = s.place().json()["id"]

    response = s.client.patch(f"{ORDERS}/{order_id}", {"notes": "x"}, format="json")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ORDER_NOT_EDITABLE"


@pytest.mark.parametrize(
    ("draft_payload", "code"),
    [({"lines": []}, "EMPTY_ORDER"), ({"warehouse_id": None}, "WAREHOUSE_REQUIRED")],
)
def test_submission_requires_lines_and_warehouse(
    s: Scenario, draft_payload: dict[str, object], code: str
) -> None:
    order_id = s.draft(**draft_payload).json()["id"]

    response = s.client.post(f"{ORDERS}/{order_id}/submit")

    assert response.json()["error"]["code"] == code
    assert s.client.get(f"{ORDERS}/{order_id}").json()["status"] == "DRAFT"


def test_a_cancelled_draft_cannot_be_submitted(s: Scenario) -> None:
    order_id = s.draft().json()["id"]
    s.client.post(f"{ORDERS}/{order_id}/cancel", {"reason": "Cliente desistiu"})

    response = s.client.post(f"{ORDERS}/{order_id}/submit")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_ORDER_TRANSITION"
    assert response.json()["error"]["details"] == {"from": "CANCELLED", "to": "PENDING"}
