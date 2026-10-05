from django.contrib import admin

from apps.pricing.models import PriceList


@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin[PriceList]):
    list_display = ("name", "segment", "organization")
    list_filter = ("organization",)
    search_fields = ("name",)
