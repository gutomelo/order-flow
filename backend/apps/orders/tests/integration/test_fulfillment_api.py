"""Separação, envio e entrega (Phase 9, docs/domain/orders.md e shipping.md)."""

from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.identity.domain.permissions import Role
from apps.identity.tests.factories import authenticated_client, make_user
from apps.inventory.application.reconciliation import find_divergences
from apps.inventory.models import StockItem, StockMovement, StockReservation
from apps.orders.application.commands.cancel_order import cancel_order
from apps.orders.application.fulfillment import mark_order_delivered
from apps.orders.tests.factories import ORDERS, Scenario, make_scenario
from apps.shipping.application.tracking import track_due_shipments
from apps.shipping.domain.provider import Label, ProviderUnavailable
from apps.shipping.models import Shipment
from shared.events.models import OutboxEvent
from shared.testing.events import drain_events

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

FAKE_PROVIDER = "apps.shipping.infrastructure.fake_provider.FakeShippingProvider"


@pytest.fixture
def s() -> Scenario:
    scenario = make_scenario(role=Role.MANAGER)  # paga, separa, despacha e cancela pago
    scenario.stock(scenario.cola, 10)
    scenario.stock(scenario.water, 10)
    return scenario


@pytest.fixture
def paid_id(s: Scenario) -> str:
    order_id = str(s.place().json()["id"])  # COLA: 2 e AGUA: 3
    paid = s.client.post(
        f"{ORDERS}/{order_id}/pay",
        {"card_token": "tok_approved"},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    assert paid.json()["status"] == "PAID"
    return order_id


def _post(s: Scenario, order_id: str, action: str, client: Any = None, **data: Any) -> Any:
    return (client or s.client).post(f"{ORDERS}/{order_id}/{action}", data, format="json")


def _ready(s: Scenario, order_id: str) -> None:
    assert _post(s, order_id, "start-picking").json()["status"] == "PROCESSING"
    assert _post(s, order_id, "complete-picking").json()["status"] == "READY_TO_SHIP"


def _item(s: Scenario, product: Any) -> StockItem:
    return StockItem.objects.get(warehouse=s.warehouse, product=product)


def _due_now(order_id: str) -> None:
    Shipment.objects.filter(order_id=order_id).update(next_check_at=timezone.now())


# Fluxo -----------------------------------------------------------------------------------------


@override_settings(FAKE_SHIPPING_TRANSIT_MINUTES=0)
def test_paid_order_goes_through_picking_and_shipping_until_the_carrier_delivers(
    s: Scenario, paid_id: str
) -> None:
    _ready(s, paid_id)

    shipped = _post(s, paid_id, "ship").json()

    assert shipped["status"] == "SHIPPED"
    assert shipped["shipment"]["carrier"] == "Transportadora Simulada"
    assert shipped["shipment"]["tracking_code"].startswith("SIM")
    assert shipped["shipment"]["status"] == "IN_TRANSIT"
    cola = _item(s, s.cola)
    assert (cola.on_hand, cola.reserved, cola.available) == (8, 0, 8)  # saiu do depósito
    sales = StockMovement.objects.filter(type="SALE", reference_id=paid_id)
    assert sorted((m.on_hand_delta, m.reserved_delta) for m in sales) == [(-3, -3), (-2, -2)]
    assert set(
        StockReservation.objects.filter(order_id=paid_id).values_list("status", flat=True)
    ) == {"CONSUMED"}
    assert find_divergences() == []

    _due_now(paid_id)
    assert track_due_shipments() == 1
    drain_events()

    body = s.client.get(f"{ORDERS}/{paid_id}").json()
    assert body["status"] == "DELIVERED"
    assert (body["shipment"]["status"], body["shipment"]["delivery_source"]) == (
        "DELIVERED",
        "PROVIDER",
    )
    last = body["history"][-1]
    assert (last["to_status"], last["changed_by"], last["reason"]) == (
        "DELIVERED",
        None,  # sistema
        "Entrega confirmada pela transportadora",
    )


def test_a_shipment_still_in_transit_is_checked_again_later(s: Scenario, paid_id: str) -> None:
    _ready(s, paid_id)
    _post(s, paid_id, "ship")  # simulada: entrega só depois de 2 min
    _due_now(paid_id)

    assert track_due_shipments() == 0

    shipment = Shipment.objects.get(order_id=paid_id)
    assert shipment.status == "IN_TRANSIT"
    assert shipment.last_checked_at is not None
    assert shipment.next_check_at is not None and shipment.next_check_at > timezone.now()


def test_an_unreachable_carrier_during_tracking_only_postpones_the_check(
    s: Scenario, paid_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ready(s, paid_id)
    _post(s, paid_id, "ship")
    _due_now(paid_id)

    def unreachable(*args: Any, **kwargs: Any) -> None:
        raise ProviderUnavailable("fora do ar")

    monkeypatch.setattr(f"{FAKE_PROVIDER}.track", unreachable)

    assert track_due_shipments() == 0
    assert Shipment.objects.get(order_id=paid_id).next_check_at > timezone.now()  # type: ignore[operator]


def test_logistics_confirms_a_delivery_by_hand(s: Scenario, paid_id: str) -> None:
    _ready(s, paid_id)
    _post(s, paid_id, "ship")

    body = _post(s, paid_id, "confirm-delivery", note=" Recebido por Maria ").json()

    assert body["status"] == "DELIVERED"
    assert body["history"][-1]["reason"] == "Recebido por Maria"
    assert body["history"][-1]["changed_by"]["id"] == str(s.user.id)
    shipment = Shipment.objects.get(order_id=paid_id)
    assert (shipment.delivery_source, shipment.delivered_by_id) == ("MANUAL", s.user.id)
    _due_now(paid_id)
    assert track_due_shipments() == 0  # já entregue: o rastreio não consulta nem publica
    assert not OutboxEvent.objects.filter(event_name="shipping.shipment.delivered").exists()


def test_manual_delivery_without_note_records_a_default_reason(s: Scenario, paid_id: str) -> None:
    _ready(s, paid_id)
    _post(s, paid_id, "ship")

    body = _post(s, paid_id, "confirm-delivery").json()

    assert body["history"][-1]["reason"] == "Entrega confirmada manualmente"


# Idempotência e transições ---------------------------------------------------------------------


@override_settings(FAKE_SHIPPING_TRANSIT_MINUTES=0)
def test_repeating_each_step_has_no_new_effect(s: Scenario, paid_id: str) -> None:
    _ready(s, paid_id)
    again = _post(s, paid_id, "complete-picking")
    _post(s, paid_id, "ship")
    shipped_again = _post(s, paid_id, "ship")
    _post(s, paid_id, "confirm-delivery")
    delivered_again = _post(s, paid_id, "confirm-delivery")
    _due_now(paid_id)
    track_due_shipments()
    drain_events()

    assert (again.status_code, shipped_again.status_code, delivered_again.status_code) == (
        200,
        200,
        200,
    )
    assert Shipment.objects.filter(order_id=paid_id).count() == 1
    assert StockMovement.objects.filter(type="SALE").count() == 2  # uma por linha, uma vez
    statuses = [h["to_status"] for h in s.client.get(f"{ORDERS}/{paid_id}").json()["history"]]
    assert statuses.count("DELIVERED") == statuses.count("SHIPPED") == 1


def test_the_delivery_event_is_applied_once(s: Scenario, paid_id: str) -> None:
    _ready(s, paid_id)
    _post(s, paid_id, "ship")
    organization_id = s.organization_id

    mark_order_delivered(organization_id, paid_id)  # type: ignore[arg-type]
    mark_order_delivered(organization_id, paid_id)  # type: ignore[arg-type]

    statuses = [h["to_status"] for h in s.client.get(f"{ORDERS}/{paid_id}").json()["history"]]
    assert statuses.count("DELIVERED") == 1


@pytest.mark.parametrize(
    ("steps", "action"),
    [
        ([], "complete-picking"),  # pular a separação
        ([], "ship"),
        ([], "confirm-delivery"),
        (["start-picking"], "ship"),
        (["start-picking", "complete-picking"], "confirm-delivery"),
    ],
)
def test_steps_cannot_be_skipped(s: Scenario, paid_id: str, steps: list[str], action: str) -> None:
    for step in steps:
        _post(s, paid_id, step)

    response = _post(s, paid_id, action)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_ORDER_TRANSITION"
    assert not Shipment.objects.exists()
    assert not StockMovement.objects.filter(type="SALE").exists()


def test_an_unpaid_order_cannot_be_picked(s: Scenario) -> None:
    order_id = s.place().json()["id"]

    response = _post(s, order_id, "start-picking")

    assert response.json()["error"]["code"] == "INVALID_ORDER_TRANSITION"


def test_a_shipped_order_can_no_longer_be_cancelled(s: Scenario, paid_id: str) -> None:
    _ready(s, paid_id)
    _post(s, paid_id, "ship")

    response = _post(s, paid_id, "cancel", reason="Cliente desistiu")

    assert response.json()["error"]["code"] == "INVALID_ORDER_TRANSITION"


def test_cancelling_an_order_ready_to_ship_gives_the_stock_back_and_refunds(
    s: Scenario, paid_id: str
) -> None:
    _ready(s, paid_id)

    body = _post(s, paid_id, "cancel", reason="Cliente desistiu").json()
    drain_events()

    assert body["status"] == "CANCELLED"
    assert _item(s, s.cola).reserved == 0
    assert s.client.get(f"{ORDERS}/{paid_id}").json()["status"] == "REFUNDED"


# Transportadora indisponível e corrida com o cancelamento --------------------------------------


def test_an_unavailable_carrier_changes_nothing_and_shipping_again_works(
    s: Scenario, paid_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ready(s, paid_id)

    def unavailable(*args: Any, **kwargs: Any) -> None:
        raise ProviderUnavailable("timeout")

    with monkeypatch.context() as patch:
        patch.setattr(f"{FAKE_PROVIDER}.create_shipment", unavailable)
        refused = _post(s, paid_id, "ship")

    assert refused.status_code == 503
    assert refused.json()["error"]["code"] == "SHIPPING_PROVIDER_UNAVAILABLE"
    assert s.client.get(f"{ORDERS}/{paid_id}").json()["status"] == "READY_TO_SHIP"
    assert not StockMovement.objects.filter(type="SALE").exists()
    assert _post(s, paid_id, "ship").json()["status"] == "SHIPPED"


def test_an_order_cancelled_while_the_label_was_requested_ships_nothing(
    s: Scenario, paid_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ready(s, paid_id)

    def cancel_meanwhile(*args: Any, **kwargs: Any) -> Label:
        cancel_order(s.organization_id, s.user.id, paid_id, reason="Desistiu")  # type: ignore[arg-type]
        return Label(carrier="Transportadora Simulada", tracking_code="SIMRACE")

    monkeypatch.setattr(f"{FAKE_PROVIDER}.create_shipment", cancel_meanwhile)

    response = _post(s, paid_id, "ship")

    assert response.json()["error"]["code"] == "INVALID_ORDER_TRANSITION"
    assert s.client.get(f"{ORDERS}/{paid_id}").json()["status"] == "CANCELLED"
    assert not Shipment.objects.exists()
    assert not StockMovement.objects.filter(type="SALE").exists()
    assert _item(s, s.cola).reserved == 0


# Autorização -----------------------------------------------------------------------------------


STEPS = ("start-picking", "complete-picking", "ship", "confirm-delivery")


@pytest.mark.parametrize("role", [Role.ADMIN, Role.MANAGER, Role.WAREHOUSE])
def test_logistics_roles_take_the_order_until_delivery(
    s: Scenario, paid_id: str, role: Role
) -> None:
    client = authenticated_client(make_user(role=role, organization=s.user.organization))

    assert [_post(s, paid_id, step, client=client).status_code for step in STEPS] == [200] * 4


@pytest.mark.parametrize("role", [Role.SALES, Role.FINANCE, Role.VIEWER])
def test_other_roles_cannot_take_any_step(s: Scenario, paid_id: str, role: Role) -> None:
    client = authenticated_client(make_user(role=role, organization=s.user.organization))
    refused = []

    for step in STEPS:  # cada passo tentado com o pedido no estado em que ele valeria
        refused.append(_post(s, paid_id, step, client=client).status_code)
        _post(s, paid_id, step)  # o gerente avança

    assert refused == [403] * 4


def test_orders_of_another_organization_are_not_found(s: Scenario, paid_id: str) -> None:
    other = authenticated_client(make_scenario(role=Role.MANAGER).user)

    for action in ("start-picking", "complete-picking", "ship", "confirm-delivery"):
        assert _post(s, paid_id, action, client=other).status_code == 404


def test_old_shipments_due_are_tracked_in_batch(s: Scenario, paid_id: str) -> None:
    _ready(s, paid_id)
    _post(s, paid_id, "ship")
    Shipment.objects.update(next_check_at=timezone.now() + timedelta(hours=1))

    assert track_due_shipments() == 0  # não vencida: nem consulta
    assert Shipment.objects.get().last_checked_at is None
