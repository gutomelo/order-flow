"""Eventos auditados (docs/domain/audit.md): pedidos, dinheiro e estoque manual."""

from apps.audit.application.recording import record
from apps.audit.domain import entries
from shared.events.base import EventEnvelope
from shared.events.bus import subscribe


@subscribe("orders.order.status_changed")
def on_order_status_changed(event: EventEnvelope) -> None:
    record(event, entries.from_order_status(event.payload))


@subscribe("payments.payment.status_changed")
def on_payment_status_changed(event: EventEnvelope) -> None:
    record(event, entries.from_payment_status(event.payload))


@subscribe("payments.refund.status_changed")
def on_refund_status_changed(event: EventEnvelope) -> None:
    record(event, entries.from_refund_status(event.payload))


@subscribe("inventory.stock.changed")
def on_stock_changed(event: EventEnvelope) -> None:
    record(event, entries.from_stock_change(event.payload))


@subscribe("inventory.reorder_point.changed")
def on_reorder_point_changed(event: EventEnvelope) -> None:
    record(event, entries.from_reorder_point(event.payload))
