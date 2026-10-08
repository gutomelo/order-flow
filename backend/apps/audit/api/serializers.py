from typing import Any

from rest_framework import serializers

from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer[AuditLog]):
    actor = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "action",
            "entity_type",
            "entity_id",
            "entity_label",
            "order_id",
            "actor",
            "reason",
            "changes",
            "occurred_at",
            "request_id",
        )
        read_only_fields = fields

    def get_actor(self, log: AuditLog) -> dict[str, Any] | None:
        user = log.actor
        return None if user is None else {"id": str(user.id), "name": user.full_name}
