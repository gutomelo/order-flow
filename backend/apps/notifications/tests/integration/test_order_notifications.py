"""E-mails do ciclo do pedido ao cliente (Phase 10, docs/domain/notifications.md)."""

import re
from datetime import timedelta
from smtplib import SMTPServerDisconnected
from typing import Any
from uuid import uuid4

import pytest
from django.core import mail
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone

from apps.customers.tests.factories import make_contact
from apps.identity.domain.permissions import Role
from apps.identity.tests.factories import authenticated_client, make_user
from apps.notifications.application.sending import (
    requeue_stale_notifications,
    send_notification,
)
from apps.notifications.models import Notification
from apps.notifications.tasks import send as send_task
from apps.orders.tests.factories import ORDERS, Scenario, make_scenario
from shared.events.bus import deliver
from shared.events.models import OutboxEvent
from shared.testing.events import drain_events

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def s() -> Scenario:
    scenario = make_scenario(role=Role.MANAGER)
    scenario.stock(scenario.cola, 10)
    scenario.stock(scenario.water, 10)
    scenario.customer.email = "compras@mercado.com"
    scenario.customer.save()
    make_contact(scenario.customer, name="Maria Souza", email="maria@mercado.com", is_primary=True)
    return scenario


def _deliver_and_send() -> list[Notification]:
    """Entrega os eventos e envia o que ficou pendente (no teste o `on_commit` não dispara)."""
    drain_events()
    for notification in Notification.objects.filter(status="PENDING").order_by("created_at"):
        send_notification(notification.id)
    return list(Notification.objects.order_by("created_at"))


def _pay(s: Scenario, order_id: str) -> None:
    s.client.post(
        f"{ORDERS}/{order_id}/pay",
        {"card_token": "tok_approved"},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )


def _kinds() -> list[str]:
    return list(Notification.objects.order_by("created_at").values_list("kind", flat=True))


def test_the_customer_follows_the_order_by_email_until_delivery(s: Scenario) -> None:
    order_id = s.place().json()["id"]
    _deliver_and_send()
    _pay(s, order_id)
    for step in ("start-picking", "complete-picking", "ship", "confirm-delivery"):
        s.client.post(f"{ORDERS}/{order_id}/{step}")

    notifications = _deliver_and_send()

    assert _kinds() == ["ORDER_CONFIRMED", "ORDER_PAID", "ORDER_SHIPPED", "ORDER_DELIVERED"]
    assert {n.status for n in notifications} == {"SENT"}
    assert [m.subject for m in mail.outbox] == [
        "Pedido #000001 confirmado — aguardando pagamento",
        "Pagamento do pedido #000001 aprovado",
        "Pedido #000001 despachado",
        "Pedido #000001 entregue",
    ]
    assert all(m.to == ["maria@mercado.com"] for m in mail.outbox)  # contato principal
    confirmed, _, shipped, _ = mail.outbox
    assert "Olá, Maria Souza." in confirmed.body
    assert "Total: R$ 13,00" in confirmed.body
    assert re.search(r"Pague até \d{2}/\d{2}/\d{4} às \d{2}:\d{2}", str(confirmed.body))
    assert "- 2 x Refrigerante Cola (COLA)" in confirmed.body
    assert "Código de rastreio: SIM" in shipped.body
    assert confirmed.extra_headers["Message-ID"] == f"<{notifications[0].id}@orderflow.local>"


def test_without_a_primary_contact_the_customer_email_is_used(s: Scenario) -> None:
    s.customer.contacts.all().delete()

    s.place()
    _deliver_and_send()

    assert mail.outbox[0].to == ["compras@mercado.com"]


def test_a_customer_without_any_email_is_recorded_as_skipped(s: Scenario) -> None:
    s.customer.contacts.all().delete()
    s.customer.email = ""
    s.customer.save()

    s.place()
    notifications = _deliver_and_send()

    assert [(n.kind, n.status, n.recipient_email) for n in notifications] == [
        ("ORDER_CONFIRMED", "SKIPPED", "")
    ]
    assert mail.outbox == []


def test_internal_steps_and_discarded_drafts_do_not_email_the_customer(s: Scenario) -> None:
    draft_id = s.draft().json()["id"]
    s.client.post(f"{ORDERS}/{draft_id}/cancel", {"reason": "Rascunho errado"})
    no_stock = s.place(s.payload(lines=[{"product_id": str(s.water.id), "quantity": 99}]))

    _deliver_and_send()

    assert no_stock.json()["status"] == "PENDING"
    assert _kinds() == []


def test_cancelling_tells_whether_the_money_comes_back(s: Scenario) -> None:
    unpaid_id = s.place().json()["id"]
    paid_id = s.place().json()["id"]
    _pay(s, paid_id)
    s.client.post(f"{ORDERS}/{unpaid_id}/cancel", {"reason": "Cliente desistiu"})
    s.client.post(f"{ORDERS}/{paid_id}/cancel", {"reason": "Cliente desistiu"})

    _deliver_and_send()  # cancelamentos + estorno do pago (outbox) + "estorno concluído"
    _deliver_and_send()

    bodies = {str(m.subject): str(m.body) for m in mail.outbox}
    assert "será estornado" not in bodies["Pedido #000001 cancelado"]
    assert "O valor pago (R$ 13,00) será estornado" in bodies["Pedido #000002 cancelado"]
    assert "Estorno do pedido #000002 concluído" in bodies
    assert "Cliente desistiu" not in "".join(bodies.values())  # motivo interno não vai ao cliente


# Entrega única ---------------------------------------------------------------------------------


def test_a_redelivered_event_does_not_create_a_second_email(s: Scenario) -> None:
    s.place()
    drain_events()
    event = OutboxEvent.objects.get(
        event_name="orders.order.status_changed", payload__to_status="AWAITING_PAYMENT"
    )
    handler = "apps.notifications.application.handlers.on_order_status_changed"

    assert deliver(str(event.id), handler) is False  # já entregue: ProcessedEvent barra
    assert Notification.objects.count() == 1


def test_the_database_rejects_a_second_notification_for_the_same_event_and_recipient(
    s: Scenario,
) -> None:
    s.place()
    drain_events()
    original = Notification.objects.get()

    with pytest.raises(IntegrityError), transaction.atomic():
        Notification.objects.create(
            organization_id=original.organization_id,
            kind=original.kind,
            status="PENDING",
            source_event_id=original.source_event_id,
            reference_id=original.reference_id,
            recipient_email=original.recipient_email,
        )


def test_sending_twice_emails_once(s: Scenario) -> None:
    s.place()
    drain_events()
    notification = Notification.objects.get()

    first = send_notification(notification.id)
    again = send_notification(notification.id)

    assert (first, again) == ("SENT", "NOOP")
    assert len(mail.outbox) == 1


# Falhas do SMTP --------------------------------------------------------------------------------


@pytest.fixture
def smtp_down(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: Any, **kwargs: Any) -> int:
        raise SMTPServerDisconnected("maria@mercado.com: conexão perdida")

    monkeypatch.setattr("django.core.mail.EmailMessage.send", fail)


@override_settings(NOTIFICATIONS_MAX_ATTEMPTS=2)
def test_an_unreachable_mail_server_is_retried_then_marked_failed(
    s: Scenario, smtp_down: None
) -> None:
    s.place()
    drain_events()
    notification = Notification.objects.get()

    first = send_notification(notification.id)
    notification.refresh_from_db()
    assert (first, notification.attempts, notification.last_error) == (
        "PENDING",
        1,
        "SMTPServerDisconnected",  # só o tipo: a mensagem do SMTP traz o endereço
    )
    assert send_notification(notification.id) == "FAILED"


def test_the_task_retries_a_transient_failure_until_the_attempts_run_out(
    s: Scenario, smtp_down: None
) -> None:
    s.place()
    drain_events()
    notification = Notification.objects.get()

    result = send_task.apply(args=(str(notification.id),))  # eager: os retries rodam na hora

    notification.refresh_from_db()
    assert result.get() == "FAILED"
    # 1 tentativa + `max_retries` (4) da task = NOTIFICATIONS_MAX_ATTEMPTS (5): alinhados.
    assert notification.attempts == 5


def test_stale_pending_notifications_are_queued_again(
    s: Scenario, monkeypatch: pytest.MonkeyPatch
) -> None:
    s.place()
    drain_events()
    queued: list[Any] = []
    monkeypatch.setattr("apps.notifications.application.sending.enqueue_send", queued.append)
    assert requeue_stale_notifications() == 0  # recém-criado: o envio normal ainda vai ocorrer

    Notification.objects.update(updated_at=timezone.now() - timedelta(minutes=11))

    assert requeue_stale_notifications() == 1
    assert queued == [Notification.objects.get().id]


# Histórico no pedido ---------------------------------------------------------------------------


def test_the_order_shows_its_notifications_with_a_masked_recipient(s: Scenario) -> None:
    order_id = s.place().json()["id"]
    _deliver_and_send()
    viewer = authenticated_client(make_user(role=Role.VIEWER, organization=s.user.organization))

    body = viewer.get(f"{ORDERS}/{order_id}/notifications").json()

    assert [(n["kind"], n["status"], n["recipient"]) for n in body] == [
        ("ORDER_CONFIRMED", "SENT", "ma***@mercado.com")
    ]
    assert body[0]["subject"] == "Pedido #000001 confirmado — aguardando pagamento"


def test_notifications_of_another_organization_are_not_revealed(s: Scenario) -> None:
    order_id = s.place().json()["id"]
    _deliver_and_send()
    other = authenticated_client(make_scenario().user)

    assert other.get(f"{ORDERS}/{order_id}/notifications").json() == []
