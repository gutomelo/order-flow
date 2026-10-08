"""Trilha de auditoria: pedidos, dinheiro e estoque (Phase 12, docs/domain/audit.md)."""

from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.application.retention import purge_expired_audit_logs
from apps.audit.models import AuditLog
from apps.identity.domain.permissions import Role
from apps.identity.tests.factories import authenticated_client, make_user
from apps.inventory.models import StockItem
from apps.inventory.tests.factories import make_warehouse
from apps.orders.tests.factories import ORDERS, Scenario, make_scenario
from apps.payments.application.reconciliation import reconcile_pending_payments
from apps.payments.models import Payment, Refund
from shared.events.bus import deliver
from shared.events.models import OutboxEvent
from shared.testing.events import drain_events

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

AUDIT = "/api/v1/audit-logs"


@pytest.fixture
def s() -> Scenario:
    scenario = make_scenario(role=Role.ADMIN)
    scenario.stock(scenario.cola, 10)
    scenario.stock(scenario.water, 10)
    return scenario


def _pay(s: Scenario, order_id: str, card: str = "tok_approved") -> Any:
    return s.client.post(
        f"{ORDERS}/{order_id}/pay",
        {"card_token": card},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )


def _trail(**filters: Any) -> list[tuple[str, str, str | None]]:
    """(ação, rótulo, ator) em ordem de ocorrência."""
    drain_events()
    logs = AuditLog.objects.filter(**filters).order_by("occurred_at", "recorded_at")
    return [(log.action, log.entity_label, log.actor.email if log.actor else None) for log in logs]


# Pedidos e dinheiro ----------------------------------------------------------------------------


def test_a_paid_and_cancelled_order_leaves_a_complete_trail(s: Scenario) -> None:
    order_id = s.place().json()["id"]
    _pay(s, order_id)
    s.client.post(f"{ORDERS}/{order_id}/cancel", {"reason": "Cliente desistiu"})
    drain_events()  # estorno roda pelo outbox e conclui; depois o pedido vira REFUNDED

    me = s.user.email
    assert _trail(order_id=order_id) == [
        ("ORDER_CREATED", "#000001", me),
        ("ORDER_STATUS_CHANGED", "#000001", me),  # PENDING → AWAITING_PAYMENT (reserva)
        ("PAYMENT_STARTED", "#000001", me),
        ("PAYMENT_APPROVED", "#000001", me),
        ("ORDER_STATUS_CHANGED", "#000001", me),  # → PAID
        ("ORDER_CANCELLED", "#000001", me),
        ("REFUND_REQUESTED", "#000001", me),
        ("REFUND_COMPLETED", "#000001", None),  # o provedor concluiu (sistema)
        ("PAYMENT_REFUNDED", "#000001", None),
        ("ORDER_STATUS_CHANGED", "#000001", None),  # CANCELLED → REFUNDED (evento)
    ]
    cancelled = AuditLog.objects.get(action="ORDER_CANCELLED")
    assert cancelled.reason == "Cliente desistiu"
    assert cancelled.changes == {"status": ["PAID", "CANCELLED"]}
    approved = AuditLog.objects.get(action="PAYMENT_APPROVED")
    assert approved.changes == {
        "status": ["PENDING", "APPROVED"],
        "amount": "13.00",
        "method": "CARD",
    }


def test_a_declined_charge_keeps_the_reason(s: Scenario) -> None:
    order_id = s.place().json()["id"]
    _pay(s, order_id, "tok_declined")
    drain_events()

    declined = AuditLog.objects.get(action="PAYMENT_DECLINED")
    assert (declined.reason, declined.actor_id) == ("insufficient_funds", s.user.id)


def test_a_charge_failed_by_reconciliation_is_attributed_to_the_system(s: Scenario) -> None:
    order_id = s.place().json()["id"]
    _pay(s, order_id, "tok_unavailable")
    Payment.objects.update(next_attempt_at=timezone.now())
    reconcile_pending_payments()
    drain_events()

    failed = AuditLog.objects.get(action="PAYMENT_FAILED")
    assert (failed.actor_id, failed.reason) == (None, "provedor não conhece a cobrança")


def test_manual_payment_and_refund_confirmation_are_attributed_to_finance(s: Scenario) -> None:
    order_id = s.place().json()["id"]
    s.client.post(
        f"{ORDERS}/{order_id}/record-payment",
        {"reference": "PIX-123"},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    s.client.post(f"{ORDERS}/{order_id}/cancel", {"reason": "Duplicado"})
    drain_events()
    refund = Refund.objects.get()
    s.client.post(f"/api/v1/refunds/{refund.id}/confirm", HTTP_IDEMPOTENCY_KEY=str(uuid4()))
    drain_events()

    recorded = AuditLog.objects.get(action="PAYMENT_RECORDED")
    assert recorded.reason == "PIX-123"
    assert AuditLog.objects.get(action="REFUND_COMPLETED").actor_id == s.user.id


def test_a_rejected_refund_and_its_retry_are_recorded(s: Scenario) -> None:
    order_id = s.place().json()["id"]
    _pay(s, order_id, "tok_refund_fails")
    s.client.post(f"{ORDERS}/{order_id}/cancel", {"reason": "Desistiu"})
    drain_events()
    refund = Refund.objects.get()
    s.client.post(f"/api/v1/refunds/{refund.id}/retry", HTTP_IDEMPOTENCY_KEY=str(uuid4()))
    drain_events()

    refund_actions = [a for a, _, _ in _trail(entity_type="REFUND")]
    assert refund_actions == [
        "REFUND_REQUESTED",
        "REFUND_FAILED",
        "REFUND_RETRIED",
        "REFUND_FAILED",
    ]
    assert AuditLog.objects.filter(action="REFUND_FAILED").first().reason == "refund_rejected"  # type: ignore[union-attr]


# Estoque ---------------------------------------------------------------------------------------


def test_manual_stock_operations_are_audited_and_order_movements_are_not(s: Scenario) -> None:
    item = StockItem.objects.get(warehouse=s.warehouse, product=s.cola)
    other = make_warehouse(organization=s.user.organization, code="CD-RJ")
    s.client.post(
        "/api/v1/inventory/adjustments",
        {
            "stock_item_id": str(item.id),
            "counted_quantity": 7,
            "expected_on_hand": 10,
            "reason": "Quebra na prateleira",
        },
    )
    s.client.post(
        "/api/v1/inventory/receipts",
        {
            "warehouse_id": str(s.warehouse.id),
            "lines": [{"product_id": str(s.cola.id), "quantity": 5}],
        },
        format="json",
    )
    s.client.post(
        "/api/v1/inventory/transfers",
        {"stock_item_id": str(item.id), "to_warehouse_id": str(other.id), "quantity": 2},
    )
    s.place()  # reserva: auditada pelo pedido, não como movimento de estoque

    stock = _trail(entity_type="STOCK_ITEM")
    assert [action for action, _, _ in stock] == [
        "STOCK_ADJUSTED",
        "STOCK_RECEIVED",
        "STOCK_TRANSFERRED",
        "STOCK_TRANSFERRED",
    ]
    adjusted = AuditLog.objects.get(action="STOCK_ADJUSTED")
    assert adjusted.changes == {"on_hand": [10, 7]}
    assert adjusted.reason == "Quebra na prateleira"
    assert adjusted.entity_label == f"COLA · {s.warehouse.code}"
    assert {log.entity_label for log in AuditLog.objects.filter(action="STOCK_TRANSFERRED")} == {
        f"COLA · {s.warehouse.code}",
        "COLA · CD-RJ",
    }


def test_reorder_point_changes_are_audited_only_when_they_change(s: Scenario) -> None:
    item = StockItem.objects.get(warehouse=s.warehouse, product=s.cola)
    url = f"/api/v1/inventory/stock-items/{item.id}"

    s.client.patch(url, {"reorder_point": 5}, format="json")
    s.client.patch(url, {"reorder_point": 5}, format="json")  # igual: nada a registrar

    assert _trail(action="REORDER_POINT_CHANGED") == [
        ("REORDER_POINT_CHANGED", f"COLA · {s.warehouse.code}", s.user.email)
    ]
    assert AuditLog.objects.get().changes == {"reorder_point": [0, 5]}


# Garantias -------------------------------------------------------------------------------------


def test_the_request_id_links_the_record_to_the_request(s: Scenario) -> None:
    s.client.post(
        ORDERS,
        s.payload(),
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
        HTTP_X_REQUEST_ID="req-auditoria-123",
    )
    drain_events()

    assert set(AuditLog.objects.values_list("request_id", flat=True)) == {"req-auditoria-123"}


def test_a_redelivered_event_does_not_duplicate_the_record(s: Scenario) -> None:
    s.place()
    drain_events()
    event = OutboxEvent.objects.filter(event_name="orders.order.status_changed").first()
    assert event is not None

    again = deliver(str(event.id), "apps.audit.application.handlers.on_order_status_changed")

    assert again is False
    assert AuditLog.objects.filter(source_event_id=event.id).count() == 1


def test_the_database_refuses_to_change_or_delete_a_record(s: Scenario) -> None:
    s.place()
    drain_events()
    log = AuditLog.objects.first()
    assert log is not None

    with pytest.raises(IntegrityError), transaction.atomic():
        AuditLog.objects.filter(id=log.id).update(reason="apagando rastros")
    with pytest.raises(IntegrityError), transaction.atomic():
        AuditLog.objects.filter(id=log.id).delete()


@override_settings(AUDIT_RETENTION_DAYS=30)
@pytest.mark.django_db(transaction=True)  # a permissão de apagar vale só até o commit da limpeza
def test_retention_removes_only_records_older_than_the_limit(s: Scenario) -> None:
    s.place()
    drain_events()
    recent = AuditLog.objects.first()
    assert recent is not None
    # Inserir é permitido (append-only barra só UPDATE/DELETE): um registro de 31 dias atrás.
    old = AuditLog.objects.create(
        organization_id=recent.organization_id,
        action=recent.action,
        entity_type=recent.entity_type,
        entity_id=recent.entity_id,
        entity_label=recent.entity_label,
        occurred_at=timezone.now() - timedelta(days=31),
        source_event_id=uuid4(),
    )
    total = AuditLog.objects.count()

    assert purge_expired_audit_logs() == 1
    assert AuditLog.objects.count() == total - 1
    assert not AuditLog.objects.filter(id=old.id).exists()
    with pytest.raises(IntegrityError), transaction.atomic():  # fora da limpeza, continua proibido
        AuditLog.objects.filter(id=recent.id).delete()


# API -------------------------------------------------------------------------------------------


def test_lists_the_trail_newest_first_with_filters(s: Scenario) -> None:
    first = s.place().json()["id"]
    second = s.place().json()["id"]
    drain_events()

    def actions(query: dict[str, Any]) -> list[str]:
        return [row["action"] for row in s.client.get(AUDIT, query).json()["results"]]

    body = s.client.get(AUDIT).json()
    assert body["results"][0]["entity_label"] == "#000002"  # mais recente primeiro
    assert body["results"][0]["actor"] == {"id": str(s.user.id), "name": s.user.full_name}
    assert actions({"order_id": first}) == ["ORDER_STATUS_CHANGED", "ORDER_CREATED"]
    assert len(actions({"action": "ORDER_CREATED"})) == 2
    assert actions({"search": "#000002", "action": "ORDER_CREATED"}) == ["ORDER_CREATED"]
    future = (timezone.now() + timedelta(hours=1)).isoformat()
    assert actions({"occurred_after": future}) == []
    assert second


@pytest.mark.parametrize(
    ("role", "status"),
    [
        (Role.ADMIN, 200),
        (Role.MANAGER, 200),
        (Role.SALES, 403),
        (Role.WAREHOUSE, 403),
        (Role.FINANCE, 403),
        (Role.VIEWER, 403),
    ],
)
def test_only_audit_readers_see_the_trail(s: Scenario, role: Role, status: int) -> None:
    client = authenticated_client(make_user(role=role, organization=s.user.organization))

    assert client.get(AUDIT).status_code == status


def test_the_trail_is_read_only_and_scoped_to_the_organization(s: Scenario) -> None:
    s.place()
    drain_events()
    stranger = authenticated_client(make_scenario(role=Role.ADMIN).user)

    assert stranger.get(AUDIT).json()["results"] == []
    assert s.client.post(AUDIT, {}).status_code == 405
    assert APIClient().get(AUDIT).status_code == 401
