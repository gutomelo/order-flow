"""Reações de `orders` a eventos de outros módulos (outbox, ADR-011)."""

from uuid import UUID

from apps.orders.application.fulfillment import mark_order_delivered
from apps.orders.application.payment_flow import apply_payment_result, mark_order_refunded
from shared.events.base import EventEnvelope
from shared.events.bus import subscribe


@subscribe("payments.payment.approved")
def on_payment_approved(event: EventEnvelope) -> None:
    payload = event.payload
    apply_payment_result(
        UUID(payload["organization_id"]), UUID(payload["order_id"]), UUID(payload["payment_id"])
    )


@subscribe("payments.payment.refunded")
def on_payment_refunded(event: EventEnvelope) -> None:
    payload = event.payload
    mark_order_refunded(UUID(payload["organization_id"]), UUID(payload["order_id"]))


@subscribe("shipping.shipment.delivered")
def on_shipment_delivered(event: EventEnvelope) -> None:
    payload = event.payload
    mark_order_delivered(UUID(payload["organization_id"]), UUID(payload["order_id"]))
