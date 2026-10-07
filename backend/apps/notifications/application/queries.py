from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from apps.notifications.domain.policies import mask_email
from apps.notifications.models import Notification


@dataclass(frozen=True)
class NotificationSummary:
    id: UUID
    kind: str
    status: str
    recipient: str  # mascarado
    subject: str
    attempts: int
    created_at: datetime
    sent_at: datetime | None


def notifications_for(organization_id: UUID, reference_id: UUID) -> list[NotificationSummary]:
    rows = (
        Notification.objects.for_organization(organization_id)
        .filter(reference_id=reference_id)
        .order_by("created_at")
    )
    return [
        NotificationSummary(
            n.id,
            n.kind,
            n.status,
            mask_email(n.recipient_email) if n.recipient_email else "",
            n.subject,
            n.attempts,
            n.created_at,
            n.sent_at,
        )
        for n in rows
    ]
