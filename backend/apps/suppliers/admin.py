from django.contrib import admin

from apps.suppliers.models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin[Supplier]):
    list_display = ("legal_name", "trade_name", "tax_id", "organization", "is_active")
    list_filter = ("organization", "is_active")
    search_fields = ("legal_name", "trade_name", "tax_id")
