"""Indicadores do dashboard: composição de leituras públicas de orders, payments e inventory.

Cache por **organização + período** (não por usuário): todos da organização veem os mesmos números,
então N pessoas com o dashboard aberto custam uma consulta por intervalo. A seção de dinheiro e a
de estoque são removidas **depois** do cache, conforme a permissão de quem pede.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.dashboard.domain.periods import Period, PeriodKey, resolve_period
from apps.inventory.application.queries import low_stock_count
from apps.orders.application.queries import (
    count_submitted_orders,
    open_orders_by_status,
    recent_orders,
    submitted_orders_by_bucket,
)
from apps.payments.application.queries import net_revenue_by_bucket, revenue_totals

CACHE_VERSION = 1
CENTS = Decimal("0.01")


def _money(value: Decimal) -> str:
    return str(value.quantize(CENTS, rounding=ROUND_HALF_UP))


def _orders_section(organization_id: UUID, period: Period) -> dict[str, Any]:
    per_slot = submitted_orders_by_bucket(organization_id, period.start, period.end, period.bucket)
    return {
        "submitted": {
            "value": sum(per_slot.values()),
            "previous": count_submitted_orders(
                organization_id, period.previous_start, period.previous_end
            ),
        },
        "series": [
            {"start": slot.isoformat(), "count": per_slot.get(slot, 0)} for slot in period.slots()
        ],
        "open_by_status": [
            {"status": status, "count": count}
            for status, count in open_orders_by_status(organization_id).items()
        ],
        "recent": [
            {
                "id": str(order.id),
                "reference": order.reference,
                "customer_name": order.customer_name,
                "status": order.status,
                "total": _money(order.total),
                "submitted_at": order.submitted_at.isoformat(),
            }
            for order in recent_orders(organization_id)
        ],
    }


def _average(total: Decimal, count: int) -> str | None:
    return _money(total / count) if count else None


def _money_section(organization_id: UUID, period: Period) -> dict[str, Any]:
    current = revenue_totals(organization_id, period.start, period.end)
    previous = revenue_totals(organization_id, period.previous_start, period.previous_end)
    per_slot = net_revenue_by_bucket(organization_id, period.start, period.end, period.bucket)
    return {
        "revenue": {"value": _money(current.net), "previous": _money(previous.net)},
        "refunded": {"value": _money(current.refunded), "previous": _money(previous.refunded)},
        "paid_orders": {"value": current.approved_count, "previous": previous.approved_count},
        "average_ticket": {
            "value": _average(current.approved, current.approved_count),
            "previous": _average(previous.approved, previous.approved_count),
        },
        "series": [
            {"start": slot.isoformat(), "net": _money(per_slot.get(slot, Decimal("0")))}
            for slot in period.slots()
        ],
    }


def build_dashboard(organization_id: UUID, key: PeriodKey, now: datetime) -> dict[str, Any]:
    period = resolve_period(key, now, settings.BUSINESS_TIME_ZONE)
    return {
        "period": key.value,
        "start": period.start.isoformat(),
        "end": period.end.isoformat(),
        "bucket": period.bucket,
        "generated_at": now.isoformat(),
        "orders": _orders_section(organization_id, period),
        "money": _money_section(organization_id, period),
        "stock": {"low_stock_items": low_stock_count(organization_id)},
    }


@dataclass(frozen=True)
class Audience:
    """O que a pessoa pode ver (decidido pelas permissões na view)."""

    money: bool  # reports:financial
    stock: bool  # inventory:read


def dashboard_for(organization_id: UUID, key: PeriodKey, audience: Audience) -> dict[str, Any]:
    cache_key = f"dashboard:v{CACHE_VERSION}:{organization_id}:{key.value}"
    seconds = settings.DASHBOARD_CACHE_SECONDS
    data = cache.get(cache_key) if seconds else None
    if data is None:
        data = build_dashboard(organization_id, key, timezone.now())
        if seconds:
            cache.set(cache_key, data, seconds)
    return {
        **data,
        "money": data["money"] if audience.money else None,
        "stock": data["stock"] if audience.stock else None,
    }
