from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin[AuditLog]):
    """Somente leitura (o banco também recusa alteração: trigger append-only)."""

    list_display = ("occurred_at", "action", "entity_label", "actor", "organization")
    list_filter = ("organization", "action", "entity_type")
    search_fields = ("entity_label", "reason", "request_id")

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object = None) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: object = None) -> bool:
        return False
