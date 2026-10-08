"""Estoque baixo: aviso a quem pode movimentar o estoque quando o disponível cruza o ponto."""

import pytest
from django.core import mail

from apps.identity.domain.permissions import Role
from apps.identity.tests.factories import make_user
from apps.inventory.models import StockItem
from apps.notifications.application.sending import send_notification
from apps.notifications.models import Notification
from apps.orders.tests.factories import Scenario, make_scenario
from shared.events.models import OutboxEvent
from shared.testing.events import drain_events

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def s() -> Scenario:
    scenario = make_scenario(role=Role.SALES)  # quem vende não cuida do estoque
    scenario.stock(scenario.cola, 10)
    scenario.stock(scenario.water, 10)
    StockItem.objects.filter(product=scenario.cola).update(reorder_point=9)
    return scenario


def _one_cola(s: Scenario) -> dict[str, object]:
    return s.payload(lines=[{"product_id": str(s.cola.id), "quantity": 1}])


def test_crossing_the_reorder_point_emails_who_handles_stock(s: Scenario) -> None:
    org = s.user.organization
    make_user(role=Role.WAREHOUSE, organization=org, email="estoque@acme.com", first_name="Rui")
    make_user(role=Role.MANAGER, organization=org, email="gerente@acme.com")
    make_user(role=Role.FINANCE, organization=org, email="financeiro@acme.com")
    make_user(role=Role.WAREHOUSE, organization=org, email="antigo@acme.com", is_active=False)

    s.place(_one_cola(s))  # 10 → 9: chegou ao ponto
    drain_events()
    for notification in Notification.objects.filter(status="PENDING"):
        send_notification(notification.id)

    assert sorted(m.to[0] for m in mail.outbox) == ["estoque@acme.com", "gerente@acme.com"]
    rui = next(m for m in mail.outbox if m.to == ["estoque@acme.com"])
    assert rui.subject.startswith("Estoque baixo: COLA em ")
    assert "Disponível agora: 9" in rui.body
    assert "Ponto de reposição: 9" in rui.body


def test_while_it_stays_low_there_is_no_new_alert(s: Scenario) -> None:
    s.place(_one_cola(s))  # 10 → 9
    s.place(_one_cola(s))  # 9 → 8: continua baixo

    assert OutboxEvent.objects.filter(event_name="inventory.stock.low").count() == 1


def test_a_failed_movement_does_not_alert(s: Scenario) -> None:
    s.place(s.payload(lines=[{"product_id": str(s.cola.id), "quantity": 99}]))  # sem estoque

    assert not OutboxEvent.objects.filter(event_name="inventory.stock.low").exists()


def test_reorder_point_zero_never_alerts() -> None:
    s = make_scenario()
    s.stock(s.cola, 2)

    s.place(s.payload(lines=[{"product_id": str(s.cola.id), "quantity": 2}]))  # 2 → 0

    assert not OutboxEvent.objects.filter(event_name="inventory.stock.low").exists()
