import uuid

from django.db import models
from django.db.models import Q

from apps.catalog.models import Product
from apps.customers.models import CustomerSegment
from shared.domain.money import DEFAULT_CURRENCY
from shared.tenancy.models import TenantScopedModel


class PriceList(TenantScopedModel):
    """Tabela de preços; sem segmento = tabela padrão da organização (docs/domain/pricing.md)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    segment = models.ForeignKey(
        CustomerSegment, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    currency = models.CharField(max_length=3, default=DEFAULT_CURRENCY)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pricing_price_list"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"], name="pricing_price_list_org_name_uniq"
            ),
            # PR1: uma tabela padrão por organização e uma por segmento.
            models.UniqueConstraint(
                fields=["organization"],
                condition=Q(segment__isnull=True),
                name="pricing_price_list_one_default_uniq",
            ),
            models.UniqueConstraint(
                fields=["organization", "segment"],
                condition=Q(segment__isnull=False),
                name="pricing_price_list_one_per_segment_uniq",
            ),
            models.CheckConstraint(
                condition=Q(currency="BRL"), name="pricing_price_list_currency_check"
            ),
        ]

    def __str__(self) -> str:
        return self.name


class PriceListItem(TenantScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    price_list = models.ForeignKey(PriceList, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="+")
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pricing_price_list_item"
        constraints = [
            models.UniqueConstraint(
                fields=["price_list", "product"], name="pricing_item_list_product_uniq"
            ),
            models.CheckConstraint(
                condition=Q(unit_price__gte=0), name="pricing_item_unit_price_non_negative_check"
            ),
        ]
        indexes = [
            # Cotação: "preço deste produto nestas tabelas".
            models.Index(fields=["product", "price_list"], name="pricing_item_product_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.product_id} @ {self.unit_price}"
