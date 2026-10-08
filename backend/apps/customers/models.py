import uuid

from django.db import models
from django.db.models import Q

from shared.tenancy.models import TenantScopedModel

SEGMENT_CODE_PATTERN = r"^[A-Z0-9_-]{2,30}$"
POSTAL_CODE_PATTERN = r"^[0-9]{8}$"


class BrazilianState(models.TextChoices):
    AC = "AC", "Acre"
    AL = "AL", "Alagoas"
    AP = "AP", "Amapá"
    AM = "AM", "Amazonas"
    BA = "BA", "Bahia"
    CE = "CE", "Ceará"
    DF = "DF", "Distrito Federal"
    ES = "ES", "Espírito Santo"
    GO = "GO", "Goiás"
    MA = "MA", "Maranhão"
    MT = "MT", "Mato Grosso"
    MS = "MS", "Mato Grosso do Sul"
    MG = "MG", "Minas Gerais"
    PA = "PA", "Pará"
    PB = "PB", "Paraíba"
    PR = "PR", "Paraná"
    PE = "PE", "Pernambuco"
    PI = "PI", "Piauí"
    RJ = "RJ", "Rio de Janeiro"
    RN = "RN", "Rio Grande do Norte"
    RS = "RS", "Rio Grande do Sul"
    RO = "RO", "Rondônia"
    RR = "RR", "Roraima"
    SC = "SC", "Santa Catarina"
    SP = "SP", "São Paulo"
    SE = "SE", "Sergipe"
    TO = "TO", "Tocantins"


class CustomerSegment(TenantScopedModel):
    """Segmento comercial definido pela organização (docs/domain/customers.md, SG1 a SG3)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customers_segment"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"], name="customers_segment_org_code_uniq"
            ),
            models.CheckConstraint(
                condition=Q(code__regex=SEGMENT_CODE_PATTERN),
                name="customers_segment_code_format_check",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class Customer(TenantScopedModel):
    """Empresa compradora (B2B)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    legal_name = models.CharField(max_length=200)
    trade_name = models.CharField(max_length=200, blank=True)
    # CNPJ normalizado (sem máscara, maiúsculas): numérico ou alfanumérico.
    tax_id = models.CharField(max_length=14)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    segment = models.ForeignKey(
        CustomerSegment, on_delete=models.PROTECT, null=True, blank=True, related_name="customers"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customers_customer"
        ordering = ("legal_name",)
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "tax_id"], name="customers_customer_org_tax_id_uniq"
            ),
            models.CheckConstraint(
                condition=Q(tax_id__regex=r"^[0-9A-Z]{12}[0-9]{2}$"),
                name="customers_customer_tax_id_format_check",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "is_active"], name="customers_org_active_idx"),
        ]

    def __str__(self) -> str:
        return self.display_name

    @property
    def display_name(self) -> str:
        return self.trade_name or self.legal_name


class CustomerAddress(TenantScopedModel):
    """Endereço do cliente; os papéis (cobrança, entrega padrão) são marcadores (AD2, AD3)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=60)
    postal_code = models.CharField(max_length=8)
    street = models.CharField(max_length=200)
    number = models.CharField(max_length=20)
    complement = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2, choices=BrazilianState.choices)
    is_billing = models.BooleanField(default=False)
    is_default_shipping = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customers_address"
        ordering = ("created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=["customer"],
                condition=Q(is_billing=True),
                name="customers_address_one_billing_uniq",
            ),
            models.UniqueConstraint(
                fields=["customer"],
                condition=Q(is_default_shipping=True),
                name="customers_address_one_default_shipping_uniq",
            ),
            models.CheckConstraint(
                condition=Q(postal_code__regex=POSTAL_CODE_PATTERN),
                name="customers_address_postal_code_format_check",
            ),
            models.CheckConstraint(
                condition=Q(state__in=BrazilianState.values),
                name="customers_address_state_check",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.label} ({self.city}/{self.state})"


class CustomerContact(TenantScopedModel):
    """Pessoa de contato do cliente — dado pessoal (LGPD): nunca vai para logs."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="contacts")
    name = models.CharField(max_length=120)
    job_title = models.CharField(max_length=80, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customers_contact"
        ordering = ("created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=["customer"],
                condition=Q(is_primary=True),
                name="customers_contact_one_primary_uniq",
            ),
            models.CheckConstraint(
                condition=~Q(email="") | ~Q(phone=""),
                name="customers_contact_channel_required_check",
            ),
        ]

    def __str__(self) -> str:
        return self.name
