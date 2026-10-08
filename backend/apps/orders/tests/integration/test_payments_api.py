"""Pagamento do pedido de ponta a ponta (Phase 8, docs/domain/payments.md e orders.md)."""

from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.identity.domain.permissions import Role
from apps.identity.tests.factories import authenticated_client, make_user
from apps.inventory.models import StockItem, StockReservation
from apps.orders.application.commands.expiration import expire_due_orders
from apps.orders.models import Order
from apps.orders.tests.factories import ORDERS, Scenario, make_scenario
from apps.payments.application.reconciliation import reconcile_pending_payments
from apps.payments.domain.gateway import GatewayUnavailable
from apps.payments.models import Payment, Refund
from shared.testing.events import drain_events

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def s() -> Scenario:
    scenario = make_scenario(role=Role.MANAGER)  # paga, cancela pago e lê pagamentos
    scenario.stock(scenario.cola, 10)
    scenario.stock(scenario.water, 10)
    return scenario


@pytest.fixture
def order_id(s: Scenario) -> str:
    body = s.place().json()
    assert body["status"] == "AWAITING_PAYMENT"
    return str(body["id"])


def _pay(s: Scenario, order_id: str, token: str, *, key: Any = None, client: Any = None) -> Any:
    return (client or s.client).post(
        f"{ORDERS}/{order_id}/pay",
        {"card_token": token},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(key or uuid4()),
    )


def _order(s: Scenario, order_id: str) -> dict[str, Any]:
    body: dict[str, Any] = s.client.get(f"{ORDERS}/{order_id}").json()
    return body


def _reservation_statuses(order_id: str) -> set[str]:
    return set(StockReservation.objects.filter(order_id=order_id).values_list("status", flat=True))


def _due_now(order_id: str) -> None:
    Payment.objects.filter(order_id=order_id).update(next_attempt_at=timezone.now())


# Aprovado / recusado ----------------------------------------------------------------------------


def test_approved_card_pays_the_order_and_confirms_the_reservation(
    s: Scenario, order_id: str
) -> None:
    response = _pay(s, order_id, "tok_approved")

    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["payment_due_at"]) == ("PAID", None)
    assert [(p["method"], p["status"], p["amount"]) for p in body["payments"]] == [
        ("CARD", "APPROVED", "13.00")
    ]
    assert body["history"][-1]["to_status"] == "PAID"
    assert _reservation_statuses(order_id) == {"CONFIRMED"}  # não expira mais
    assert StockItem.objects.get(product=s.cola).reserved == 2  # segue reservado até o envio
    drain_events()  # o evento de aprovação chega depois: idempotente, nada muda
    assert _order(s, order_id)["status"] == "PAID"


def test_declined_card_keeps_the_order_waiting_and_replays_the_same_answer(
    s: Scenario, order_id: str
) -> None:
    key = uuid4()

    first = _pay(s, order_id, "tok_declined", key=key)
    replay = _pay(s, order_id, "tok_declined", key=key)

    assert first.status_code == 422
    assert first.json()["error"]["code"] == "PAYMENT_DECLINED"
    assert first.json()["error"]["details"]["reason"] == "insufficient_funds"
    assert replay.status_code == 422 and replay["Idempotent-Replayed"] == "true"
    assert Payment.objects.filter(order_id=order_id).count() == 1  # não tentou de novo
    assert _order(s, order_id)["status"] == "AWAITING_PAYMENT"
    # Outra tentativa (outro cartão = outra intenção, outra chave) pode aprovar.
    assert _pay(s, order_id, "tok_approved").json()["status"] == "PAID"


def test_only_awaiting_orders_can_be_paid(s: Scenario) -> None:
    pending_id = s.place(s.payload(lines=[{"product_id": str(s.cola.id), "quantity": 99}])).json()[
        "id"
    ]

    response = _pay(s, pending_id, "tok_approved")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ORDER_NOT_AWAITING_PAYMENT"


def test_card_token_is_never_stored(s: Scenario, order_id: str) -> None:
    _pay(s, order_id, "tok_approved")

    stored = Payment.objects.filter(order_id=order_id).values().get()
    assert "tok_approved" not in str(stored)


# Timeout e reconciliação ------------------------------------------------------------------------


def test_timeout_answers_202_and_reconciliation_completes_the_payment(
    s: Scenario, order_id: str
) -> None:
    response = _pay(s, order_id, "tok_timeout")

    assert response.status_code == 202
    assert response.json()["status"] == "AWAITING_PAYMENT"
    assert response.json()["payments"][0]["status"] == "PENDING"
    retry = _pay(s, order_id, "tok_approved")
    assert retry.json()["error"]["code"] == "PAYMENT_IN_PROGRESS"  # nunca duas cobranças vivas

    _due_now(order_id)
    assert reconcile_pending_payments() == 1
    drain_events()

    assert _order(s, order_id)["status"] == "PAID"


def test_a_charge_the_provider_never_received_fails_at_the_first_check(
    s: Scenario, order_id: str
) -> None:
    assert _pay(s, order_id, "tok_unavailable").status_code == 202

    _due_now(order_id)
    reconcile_pending_payments()  # o provedor responde que não conhece a chave: nada foi cobrado

    assert Payment.objects.get(order_id=order_id).status == "FAILED"
    assert _order(s, order_id)["status"] == "AWAITING_PAYMENT"
    assert _pay(s, order_id, "tok_approved").json()["status"] == "PAID"  # liberado na hora


@override_settings(PAYMENT_RECONCILIATION_MAX_ATTEMPTS=2)
def test_while_the_provider_does_not_answer_the_check_is_retried_with_backoff(
    s: Scenario, order_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _pay(s, order_id, "tok_unavailable").status_code == 202

    def unreachable(*args: Any, **kwargs: Any) -> None:
        raise GatewayUnavailable("fora do ar")

    # Só a fronteira com o provedor é trocada (o adapter fake), por caminho: `orders` não importa
    # a infraestrutura de `payments`.
    monkeypatch.setattr(
        "apps.payments.infrastructure.fake_gateway.FakePaymentGateway.get_charge", unreachable
    )
    _due_now(order_id)
    reconcile_pending_payments()  # sem resposta: não dá para saber → consulta de novo depois
    payment = Payment.objects.get(order_id=order_id)
    assert (payment.status, payment.attempts) == ("PENDING", 1)
    assert payment.next_attempt_at is not None and payment.next_attempt_at > timezone.now()
    _due_now(order_id)
    reconcile_pending_payments()

    assert Payment.objects.get(order_id=order_id).status == "FAILED"  # limite de tentativas


def test_reservation_does_not_expire_while_a_charge_is_in_flight(
    s: Scenario, order_id: str
) -> None:
    _pay(s, order_id, "tok_timeout")
    Order.objects.filter(id=order_id).update(payment_due_at=timezone.now() - timedelta(minutes=1))

    assert expire_due_orders() == 0
    assert _order(s, order_id)["status"] == "AWAITING_PAYMENT"


# Aprovação tardia ------------------------------------------------------------------------------


def _approved_after(s: Scenario, order_id: str, change: str) -> None:
    """Cobrança em timeout; algo muda no pedido; a reconciliação aprova depois."""
    _pay(s, order_id, "tok_timeout")
    if change == "cancelled":
        s.client.post(f"{ORDERS}/{order_id}/cancel", {"reason": "Cliente desistiu"})
    else:  # reserva expirou (forçado: o job pula pedidos com cobrança em voo)
        from apps.orders.application.reservations import release_order_stock
        from apps.orders.application.transitions import transition
        from apps.orders.domain.status import OrderStatus

        order = Order.objects.get(id=order_id)
        release_order_stock(order, None, expired=True)
        transition(order, OrderStatus.PENDING, actor_id=None, reason="teste")
        if change == "expired_no_stock":
            StockItem.objects.filter(product=s.cola).update(on_hand=0)
    _due_now(order_id)
    reconcile_pending_payments()
    drain_events()


def test_late_approval_after_expiry_reserves_again_when_there_is_stock(
    s: Scenario, order_id: str
) -> None:
    _approved_after(s, order_id, "expired_with_stock")

    assert _order(s, order_id)["status"] == "PAID"


def test_late_approval_without_stock_refunds_and_leaves_the_order_pending(
    s: Scenario, order_id: str
) -> None:
    _approved_after(s, order_id, "expired_no_stock")

    order = _order(s, order_id)
    assert order["status"] == "PENDING"
    assert [(p["status"], [r["status"] for r in p["refunds"]]) for p in order["payments"]] == [
        ("REFUNDED", ["SUCCEEDED"])
    ]


def test_approval_after_cancellation_is_refunded(s: Scenario, order_id: str) -> None:
    _approved_after(s, order_id, "cancelled")

    order = _order(s, order_id)
    assert order["status"] == "REFUNDED"
    assert order["payments"][0]["status"] == "REFUNDED"


# Cancelamento de pedido pago e estorno ----------------------------------------------------------


def test_cancelling_a_paid_order_releases_stock_and_refunds(s: Scenario, order_id: str) -> None:
    _pay(s, order_id, "tok_approved")

    cancelled = s.client.post(f"{ORDERS}/{order_id}/cancel", {"reason": "Cliente desistiu"})
    assert cancelled.json()["status"] == "CANCELLED"
    assert _reservation_statuses(order_id) == {"RELEASED"}
    assert StockItem.objects.get(product=s.cola).reserved == 0
    assert Refund.objects.get().status == "PENDING"  # sai pelo outbox, depois do commit

    drain_events()

    order = _order(s, order_id)
    assert order["status"] == "REFUNDED"
    assert [h["to_status"] for h in order["history"]][-2:] == ["CANCELLED", "REFUNDED"]


def test_cancelling_a_paid_order_requires_cancel_paid(s: Scenario, order_id: str) -> None:
    _pay(s, order_id, "tok_approved")
    seller = authenticated_client(make_user(role=Role.SALES, organization=s.user.organization))

    response = seller.post(f"{ORDERS}/{order_id}/cancel", {"reason": "x"})

    assert response.status_code == 403
    assert _order(s, order_id)["status"] == "PAID"


def test_a_refund_rejected_by_the_provider_can_be_retried_by_finance(
    s: Scenario, order_id: str
) -> None:
    _pay(s, order_id, "tok_refund_fails")
    s.client.post(f"{ORDERS}/{order_id}/cancel", {"reason": "Cliente desistiu"})
    drain_events()
    refund = Refund.objects.get()
    assert (refund.status, refund.failure_reason) == ("FAILED", "refund_rejected")
    assert _order(s, order_id)["status"] == "CANCELLED"  # dinheiro ainda não voltou
    finance = authenticated_client(make_user(role=Role.FINANCE, organization=s.user.organization))

    retried = finance.post(f"/api/v1/refunds/{refund.id}/retry", HTTP_IDEMPOTENCY_KEY=str(uuid4()))

    assert (retried.json()["status"], retried.json()["failure_reason"]) == ("PENDING", "")
    drain_events()
    assert Refund.objects.get().status == "FAILED"  # o provedor recusou de novo; segue visível
    again = finance.post(f"/api/v1/refunds/{refund.id}/confirm", HTTP_IDEMPOTENCY_KEY=str(uuid4()))
    assert again.json()["error"]["code"] == "REFUND_NOT_MANUAL"


# Baixa manual ----------------------------------------------------------------------------------


def test_finance_records_a_manual_payment_and_confirms_its_refund(
    s: Scenario, order_id: str
) -> None:
    finance = authenticated_client(make_user(role=Role.FINANCE, organization=s.user.organization))

    paid = finance.post(
        f"{ORDERS}/{order_id}/record-payment",
        {"reference": "PIX E2E 123"},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )

    assert paid.json()["status"] == "PAID"
    assert paid.json()["payments"][0]["manual_reference"] == "PIX E2E 123"
    finance.post(f"{ORDERS}/{order_id}/cancel", {"reason": "Devolução combinada"})
    drain_events()
    refund = Refund.objects.get()
    assert refund.status == "PENDING"  # manual: aguarda o financeiro devolver fora do sistema
    finance.post(f"/api/v1/refunds/{refund.id}/confirm", HTTP_IDEMPOTENCY_KEY=str(uuid4()))
    drain_events()
    assert _order(s, order_id)["status"] == "REFUNDED"


def test_manual_payment_needs_a_reference(s: Scenario, order_id: str) -> None:
    response = s.client.post(
        f"{ORDERS}/{order_id}/record-payment",
        {"reference": ""},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )

    assert response.status_code == 400


# Leitura e permissões --------------------------------------------------------------------------


def test_finance_lists_payments_with_refunds(s: Scenario, order_id: str) -> None:
    _pay(s, order_id, "tok_approved")
    finance = authenticated_client(make_user(role=Role.FINANCE, organization=s.user.organization))
    seller = authenticated_client(make_user(role=Role.SALES, organization=s.user.organization))

    listed = finance.get("/api/v1/payments").json()["results"]

    assert [(p["order_reference"], p["status"]) for p in listed] == [("#000001", "APPROVED")]
    assert seller.get("/api/v1/payments").status_code == 403
    assert make_scenario().client.get("/api/v1/payments").status_code == 403  # SALES de outra org


@pytest.mark.parametrize(("role", "expected"), [(Role.VIEWER, 403), (Role.WAREHOUSE, 403)])
def test_paying_requires_payments_create(
    s: Scenario, order_id: str, role: Role, expected: int
) -> None:
    client = authenticated_client(make_user(role=role, organization=s.user.organization))

    assert _pay(s, order_id, "tok_approved", client=client).status_code == expected
