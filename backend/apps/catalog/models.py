import uuid

from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower

from shared.tenancy.models import TenantScopedModel

MAX_CATEGORY_DEPTH = 3
SKU_PATTERN = r"^[A-Z0-9][A-Z0-9._-]{0,63}$"


class UnitOfMeasure(models.TextChoices):
    # Quantidades são inteiras no MVP (docs/domain/catalog.md, regra C5).
    UNIT = "UNIT", "Unidade"
    BOX = "BOX", "Caixa"
    PACK = "PACK", "Pacote"
    PAIR = "PAIR", "Par"


class Category(TenantScopedModel):
    """Categoria hierárquica de produtos (até 3 níveis)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="children"
    )
    # Persistido para limitar a profundidade no banco e montar a árvore sem recursão.
    depth = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "catalog_category"
        ordering = ("name",)
        verbose_name_plural = "categories"
        constraints = [
            # K3: nome único entre irmãs; NULLS NOT DISTINCT faz valer também para as raízes.
            models.UniqueConstraint(
                F("organization"),
                F("parent"),
                Lower("name"),
                name="catalog_category_org_parent_name_uniq",
                nulls_distinct=False,
            ),
            models.CheckConstraint(
                condition=Q(depth__gte=1) & Q(depth__lte=MAX_CATEGORY_DEPTH),
                name="catalog_category_depth_range_check",
            ),
            models.CheckConstraint(
                condition=(Q(parent__isnull=True) & Q(depth=1))
                | (Q(parent__isnull=False) & Q(depth__gt=1)),
                name="catalog_category_root_depth_check",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Product(TenantScopedModel):
    """Item vendável identificado por SKU. Sem preço: preços são do módulo `pricing`."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.CharField(max_length=64)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, null=True, blank=True, related_name="products"
    )
    default_supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    unit = models.CharField(
        max_length=10, choices=UnitOfMeasure.choices, default=UnitOfMeasure.UNIT
    )
    # GTIN opcional (EAN-13 etc.); string vazia quando ausente.
    barcode = models.CharField(max_length=14, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "catalog_product"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "sku"], name="catalog_product_org_sku_uniq"
            ),
            models.UniqueConstraint(
                fields=["organization", "barcode"],
                condition=~Q(barcode=""),
                name="catalog_product_org_barcode_uniq",
            ),
            models.CheckConstraint(
                condition=Q(sku__regex=SKU_PATTERN), name="catalog_product_sku_format_check"
            ),
            models.CheckConstraint(
                condition=Q(unit__in=UnitOfMeasure.values), name="catalog_product_unit_check"
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "is_active", "name"], name="catalog_product_list_idx"
            ),
            models.Index(fields=["organization", "category"], name="catalog_product_category_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.sku} — {self.name}"
