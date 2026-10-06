from uuid import UUID

from apps.payments.application.refunds import process_refund
from shared.events.base import EventEnvelope
from shared.events.bus import subscribe


@subscribe("payments.refund.requested")
def execute_requested_refund(event: EventEnvelope) -> None:
    process_refund(UUID(event.payload["refund_id"]))
