from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.inventory.api.views import (
    AdjustmentView,
    ReceiptView,
    StockItemViewSet,
    StockMovementViewSet,
    TransferView,
    WarehouseViewSet,
)

router = SimpleRouter(trailing_slash=False)
router.register("inventory/warehouses", WarehouseViewSet, basename="warehouse")
router.register("inventory/stock-items", StockItemViewSet, basename="stock-item")
router.register("inventory/movements", StockMovementViewSet, basename="stock-movement")

urlpatterns = [
    path("inventory/receipts", ReceiptView.as_view(), name="inventory-receipts"),
    path("inventory/adjustments", AdjustmentView.as_view(), name="inventory-adjustments"),
    path("inventory/transfers", TransferView.as_view(), name="inventory-transfers"),
    *router.urls,
]
