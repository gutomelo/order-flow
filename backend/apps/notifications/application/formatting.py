"""Formatos pt-BR para o texto dos e-mails (e-mail não tem o fuso nem o locale do navegador)."""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings


def money(value: Decimal, currency: str = "BRL") -> str:
    """`Decimal("1234.5")` → `R$ 1.234,50` (só BRL no MVP)."""
    text = f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {text}" if currency == "BRL" else f"{currency} {text}"


def local_datetime(value: datetime) -> str:
    local = value.astimezone(ZoneInfo(settings.BUSINESS_TIME_ZONE))
    return local.strftime("%d/%m/%Y às %H:%M")
