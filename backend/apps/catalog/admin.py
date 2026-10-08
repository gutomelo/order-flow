from django.contrib import admin

from apps.catalog.models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin[Category]):
    list_display = ("name", "parent", "depth", "organization", "is_active")
    list_filter = ("organization", "is_active", "depth")
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin[Product]):
    list_display = ("sku", "name", "category", "unit", "organization", "is_active")
    list_filter = ("organization", "is_active", "unit")
    search_fields = ("sku", "name", "barcode")
