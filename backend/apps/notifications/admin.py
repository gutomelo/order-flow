from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin[Notification]):
    """Somente leitura: histórico de envios."""

    list_display = ("kind", "status", "subject", "attempts", "created_at", "sent_at")
    list_filter = ("organization", "kind", "status")

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object = None) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: object = None) -> bool:
        return False
