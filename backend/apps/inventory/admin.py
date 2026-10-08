from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from apps.inventory.models import StockItem, StockMovement, StockReceipt, Warehouse


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin[Warehouse]):
    list_display = ("code", "name", "organization", "is_active")
    list_filter = ("organization", "is_active")


class ReadOnlyAdmin[M: Any](admin.ModelAdmin[M]):
    """Saldo e histórico só mudam pelos casos de uso (ledger) — o admin apenas consulta."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False


@admin.register(StockItem)
class StockItemAdmin(ReadOnlyAdmin[StockItem]):
    list_display = ("product", "warehouse", "on_hand", "reserved", "available", "organization")
    list_filter = ("organization", "warehouse")


@admin.register(StockMovement)
class StockMovementAdmin(ReadOnlyAdmin[StockMovement]):
    list_display = ("created_at", "type", "stock_item", "on_hand_delta", "on_hand_after")
    list_filter = ("organization", "type")


@admin.register(StockReceipt)
class StockReceiptAdmin(ReadOnlyAdmin[StockReceipt]):
    list_display = ("created_at", "warehouse", "supplier", "document_number")
