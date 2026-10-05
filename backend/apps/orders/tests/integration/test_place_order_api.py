from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest

from apps.catalog.tests.factories import make_product
from apps.customers.tests.factories import make_address, make_customer, make_segment
from apps.inventory.tests.factories import make_warehouse
from apps.orders.models import Order
from apps.orders.tests.factories import Scenario, make_scenario
from apps.pricing.tests.factories import make_price_list, set_price

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def s() -> Scenario:
    return make_scenario()


def test_places_a_pending_order_with_frozen_prices_and_a_copy_of_the_address(s: Scenario) -> None:
    response = s.place()

    assert response.status_code == 201
    body = response.json()
    assert (body["status"], body["number"]) == ("PENDING", 1)
    assert (body["subtotal"], body["total"]) == ("13.00", "13.00")  # 2 x 3,50 + 3 x 2,00
    fields = ("sku", "quantity", "unit_price", "line_total", "price_source")
    assert [tuple(line[f] for f in fields) for line in body["lines"]] == [
        ("COLA", 2, "3.50", "7.00", "DEFAULT"),
        ("AGUA", 3, "2.00", "6.00", "DEFAULT"),
    ]
    assert body["shipping"]["address_id"] == str(s.address.id)
    assert body["shipping"]["postal_code"] == s.address.postal_code
    assert [(h["from_status"], h["to_status"]) for h in body["history"]] == [(None, "PENDING")]
    assert body["history"][0]["changed_by"]["id"] == str(s.user.id)


def test_numbers_are_sequential_per_organization(s: Scenario) -> None:
    other = make_scenario()

    first, second = s.place(), s.place()
    other_first = other.place()

    assert (first.json()["number"], second.json()["number"]) == (1, 2)
    assert other_first.json()["number"] == 1


def test_segment_price_is_used_for_customers_of_the_segment(s: Scenario) -> None:
    segment = make_segment(organization=s.user.organization)
    s.customer.segment = segment
    s.customer.save()
    set_price(make_price_list(s.organization_id, name="Atacado", segment=segment), s.cola, "2.90")

    lines = s.place().json()["lines"]

    assert [(line["sku"], line["unit_price"], line["price_source"]) for line in lines] == [
        ("COLA", "2.90", "SEGMENT"),
        ("AGUA", "2.00", "DEFAULT"),
    ]


def test_later_changes_do_not_touch_a_submitted_order(s: Scenario) -> None:
    order_id = s.place().json()["id"]
    s.price_list.items.filter(product=s.cola).update(unit_price=Decimal("9.99"))
    s.cola.name = "Cola Nova Fórmula"
    s.cola.save()
    s.address.street = "Outra Rua"
    s.address.save()

    body = s.client.get(f"/api/v1/orders/{order_id}").json()

    assert body["lines"][0]["unit_price"] == "3.50"
    assert body["lines"][0]["product_name"] == "Refrigerante Cola"
    assert body["shipping"]["street"] == "Avenida Paulista"


def test_the_seller_can_choose_another_address_of_the_customer(s: Scenario) -> None:
    branch = make_address(s.customer, label="Filial")

    body = s.place(s.payload(shipping_address_id=str(branch.id))).json()

    assert body["shipping"]["label"] == "Filial"


# Idempotência (ADR-012) ------------------------------------------------------------------------


def test_repeating_the_same_key_returns_the_same_order(s: Scenario) -> None:
    key = uuid4()

    first = s.place(key=key)
    second = s.place(key=key)

    assert second.status_code == 201
    assert second.json() == first.json()
    assert second["Idempotent-Replayed"] == "true"
    assert Order.objects.filter(organization_id=s.organization_id).count() == 1


def test_reusing_a_key_with_another_body_is_rejected(s: Scenario) -> None:
    key = uuid4()
    s.place(key=key)

    response = s.place(s.payload(notes="outro"), key=key)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


@pytest.mark.parametrize("header", [None, "não-é-uuid"])
def test_the_key_is_required(s: Scenario, header: str | None) -> None:
    extra: dict[str, Any] = {} if header is None else {"HTTP_IDEMPOTENCY_KEY": header}

    response = s.client.post("/api/v1/orders", s.payload(), format="json", **extra)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert not Order.objects.exists()


def test_a_failed_attempt_does_not_burn_the_key(s: Scenario) -> None:
    key = uuid4()
    s.price_list.items.filter(product=s.water).delete()

    failed = s.place(key=key)
    set_price(s.price_list, s.water, "2.00")
    retried = s.place(key=key)

    assert failed.json()["error"]["code"] == "PRICE_NOT_FOUND"
    assert retried.status_code == 201
    assert retried.json()["number"] == 1  # a falha também não consumiu número


# Regras e erros --------------------------------------------------------------------------------


def test_expected_total_protects_against_price_changes(s: Scenario) -> None:
    response = s.place(s.payload(expected_total="12.00"))

    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "PRICES_CHANGED",
        "message": "Os preços mudaram desde a última prévia. Confira o novo total e envie de novo.",
        "details": {"expected": "12.00", "actual": "13.00"},
    }
    assert not Order.objects.exists()
    assert s.place(s.payload(expected_total="13.00")).status_code == 201


@pytest.mark.parametrize(
    ("change", "code", "details"),
    [
        ("inactive_customer", "CUSTOMER_INACTIVE", {"field": "customer_id"}),
        ("inactive_product", "PRODUCT_UNAVAILABLE", "cola"),
        ("unpriced_product", "PRICE_NOT_FOUND", "cola"),
        ("duplicated_line", "DUPLICATE_ORDER_LINE", "cola"),
        ("zero_quantity", "INVALID_QUANTITY", "cola"),
        ("no_lines", "EMPTY_ORDER", {}),
        ("no_warehouse", "WAREHOUSE_REQUIRED", {"field": "warehouse_id"}),
        ("inactive_warehouse", "WAREHOUSE_NOT_AVAILABLE", {"field": "warehouse_id"}),
        ("foreign_address", "ADDRESS_NOT_AVAILABLE", {"field": "shipping_address_id"}),
        ("customer_without_address", "ADDRESS_REQUIRED", {"field": "shipping_address_id"}),
    ],
)
def test_invalid_orders_are_rejected_without_side_effects(
    s: Scenario, change: str, code: str, details: object
) -> None:
    cola_line = {"product_id": str(s.cola.id), "quantity": 1}
    payload = s.payload()
    if change == "inactive_customer":
        s.customer.is_active = False
        s.customer.save()
    elif change == "inactive_product":
        s.cola.is_active = False
        s.cola.save()
    elif change == "unpriced_product":
        s.price_list.items.filter(product=s.cola).delete()
    elif change == "duplicated_line":
        payload["lines"] = [cola_line, cola_line]
    elif change == "zero_quantity":
        payload["lines"] = [{**cola_line, "quantity": 0}]
    elif change == "no_lines":
        payload["lines"] = []
    elif change == "no_warehouse":
        payload["warehouse_id"] = None
    elif change == "inactive_warehouse":
        closed = make_warehouse(organization=s.user.organization, is_active=False)
        payload["warehouse_id"] = str(closed.id)
    elif change == "foreign_address":
        other = make_customer(organization=s.user.organization)
        payload["shipping_address_id"] = str(make_address(other).id)
    elif change == "customer_without_address":
        s.address.delete()

    response = s.place(payload)

    assert response.status_code in (409, 422)
    error = response.json()["error"]
    assert error["code"] == code
    expected = {"product_ids": [str(s.cola.id)]} if details == "cola" else details
    assert error["details"] == expected
    assert not Order.objects.exists()


def test_product_of_another_organization_is_unavailable(s: Scenario) -> None:
    foreign = make_product()
    payload = s.payload(lines=[{"product_id": str(foreign.id), "quantity": 1}])

    response = s.place(payload)

    assert response.json()["error"]["code"] == "PRODUCT_UNAVAILABLE"
