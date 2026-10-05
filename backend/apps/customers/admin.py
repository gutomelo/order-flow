from django.contrib import admin

from apps.customers.models import Customer, CustomerSegment


@admin.register(CustomerSegment)
class CustomerSegmentAdmin(admin.ModelAdmin[CustomerSegment]):
    list_display = ("code", "name", "organization", "is_active")
    list_filter = ("organization", "is_active")
    search_fields = ("code", "name")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin[Customer]):
    list_display = ("legal_name", "trade_name", "tax_id", "segment", "organization", "is_active")
    list_filter = ("organization", "is_active")
    search_fields = ("legal_name", "trade_name", "tax_id")
