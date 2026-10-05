from django.contrib import admin

from apps.orders.models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin[Order]):
    """Somente leitura: status só muda pela máquina de estados (O10)."""

    list_display = ("number", "status", "customer", "total", "organization", "created_at")
    list_filter = ("organization", "status")
    search_fields = ("number", "customer__legal_name")

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object = None) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: object = None) -> bool:
        return False
