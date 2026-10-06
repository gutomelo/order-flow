from django.contrib import admin

from apps.payments.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin[Payment]):
    """Somente leitura: registro financeiro nunca é editado à mão (P6)."""

    list_display = ("order_reference", "method", "status", "amount", "organization", "created_at")
    list_filter = ("organization", "status", "method")

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object = None) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: object = None) -> bool:
        return False
