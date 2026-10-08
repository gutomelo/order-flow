from django.contrib import admin

from apps.shipping.models import Shipment


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin[Shipment]):
    """Somente leitura: a remessa muda pelo fluxo do pedido e pelo rastreio."""

    list_display = ("order_reference", "carrier", "tracking_code", "status", "shipped_at")
    list_filter = ("organization", "status", "carrier")
    search_fields = ("order_reference", "tracking_code")

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object = None) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: object = None) -> bool:
        return False
