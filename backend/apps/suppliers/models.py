import uuid

from django.db import models
from django.db.models import Q

from shared.tenancy.models import TenantScopedModel


class Supplier(TenantScopedModel):
    """Empresa fornecedora (docs/domain/suppliers.md)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    legal_name = models.CharField(max_length=200)
    trade_name = models.CharField(max_length=200, blank=True)
    # CNPJ normalizado (sem máscara, maiúsculas): numérico ou alfanumérico.
    tax_id = models.CharField(max_length=14)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "suppliers_supplier"
        ordering = ("legal_name",)
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "tax_id"], name="suppliers_supplier_org_tax_id_uniq"
            ),
            models.CheckConstraint(
                condition=Q(tax_id__regex=r"^[0-9A-Z]{12}[0-9]{2}$"),
                name="suppliers_supplier_tax_id_format_check",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "is_active"], name="suppliers_org_active_idx"),
        ]

    def __str__(self) -> str:
        return self.display_name

    @property
    def display_name(self) -> str:
        return self.trade_name or self.legal_name
