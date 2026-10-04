from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.identity.models import Organization, Team, User


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin[Organization]):
    list_display = ("name", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin[Team]):
    list_display = ("name", "organization")
    list_filter = ("organization",)
    search_fields = ("name",)


@admin.register(User)
class UserAdmin(DjangoUserAdmin[User]):
    # Login por e-mail: ajusta os formulários do admin padrão, que assumem `username`.
    ordering = ("email",)
    list_display = ("email", "organization", "role", "is_active", "is_superuser")
    list_filter = ("organization", "role", "is_active", "is_superuser")
    search_fields = ("email", "first_name", "last_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Perfil", {"fields": ("first_name", "last_name")}),
        ("Organização", {"fields": ("organization", "role", "team")}),
        ("Plataforma", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Datas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "organization", "role", "password1", "password2"),
            },
        ),
    )
