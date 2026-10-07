"""Indicadores do dashboard (Phase 11, docs/domain/dashboard.md)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone

from apps.dashboard.application.metrics import build_dashboard
from apps.dashboard.domain.periods import PeriodKey
from apps.identity.domain.permissions import Role
from apps.identity.tests.factories import authenticated_client, make_user
from apps.inventory.models import StockItem
from apps.orders.models import Order
from apps.orders.tests.factories import Scenario, make_scenario
from apps.payments.models import Payment, Refund

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

URL = "/api/v1/dashboard"
NOW = datetime(2026, 10, 7, 18, 30, tzinfo=UTC)  # 15:30 em São Paulo


@pytest.fixture
def s() -> Scenario:
    scenario = make_scenario(role=Role.MANAGER)
    scenario.stock(scenario.cola, 50)
    scenario.stock(scenario.water, 50)
    return scenario


def _order(s: Scenario, submitted_at: datetime | None = None) -> str:
    order_id = str(s.place().json()["id"])
    if submitted_at:
        Order.objects.filter(id=order_id).update(submitted_at=submitted_at)
    return order_id


def _payment(s: Scenario, amount: str, at: datetime, status: str = "APPROVED") -> Payment:
    return Payment.objects.create(
        organization_id=s.organization_id,
        order_id=uuid4(),
        order_reference="#X",
        method="MANUAL",
        manual_reference="PIX",
        amount=Decimal(amount),
        status=status,
        # Como no sistema: aprovado, recusado e falho ganham data de conclusão; pendente não.
        completed_at=None if status == "PENDING" else at,
        created_by=s.user,
    )


def _refund(s: Scenario, payment: Payment, at: datetime) -> None:
    Refund.objects.create(
        organization_id=s.organization_id,
        payment=payment,
        amount=payment.amount,
        status="SUCCEEDED",
        completed_at=at,
    )


def _build(s: Scenario, key: str = "today") -> dict[str, Any]:
    return build_dashboard(s.organization_id, PeriodKey(key), NOW)


# Pedidos ---------------------------------------------------------------------------------------


def test_counts_orders_submitted_in_the_period_against_the_previous_one(s: Scenario) -> None:
    _order(s, NOW - timedelta(hours=1))  # hoje 14:30
    _order(s, NOW - timedelta(hours=15))  # hoje 00:30
    _order(s, NOW - timedelta(hours=16))  # ontem 23:30: fora de "hoje"…
    _order(s, NOW - timedelta(days=1, hours=1))  # ontem 14:30: no período anterior
    s.draft()  # rascunho nunca conta

    orders = _build(s)["orders"]

    assert orders["submitted"] == {"value": 2, "previous": 1}  # ontem 23:30 é depois das 15:30
    by_hour = {slot["start"][11:13]: slot["count"] for slot in orders["series"]}
    assert (by_hour["00"], by_hour["14"], by_hour["15"]) == (1, 1, 0)
    assert len(orders["series"]) == 16


def test_the_last_7_days_are_counted_by_business_day(s: Scenario) -> None:
    for days_ago in (0, 0, 3, 6, 7, 13):  # 1 min antes de "agora": o período é [início, agora)
        _order(s, NOW - timedelta(days=days_ago, minutes=1))

    orders = _build(s, "7d")["orders"]

    assert orders["submitted"] == {"value": 4, "previous": 2}
    assert [slot["count"] for slot in orders["series"]] == [1, 0, 0, 1, 0, 0, 2]


def test_a_late_evening_order_belongs_to_that_business_day_not_the_utc_one(s: Scenario) -> None:
    _order(s, datetime(2026, 10, 7, 1, 0, tzinfo=UTC))  # 06/10 às 22:00 em São Paulo

    series = _build(s, "7d")["orders"]["series"]

    assert {slot["start"][:10]: slot["count"] for slot in series if slot["count"]} == {
        "2026-10-06": 1
    }


def test_shows_the_current_pipeline_and_the_most_recent_orders(s: Scenario) -> None:
    ids = [_order(s, NOW - timedelta(minutes=10 * i + 1)) for i in range(7)]
    no_stock = s.payload(lines=[{"product_id": str(s.water.id), "quantity": 999}])
    pending_id = s.place(no_stock).json()["id"]
    Order.objects.filter(id=pending_id).update(submitted_at=NOW - timedelta(minutes=5))

    orders = _build(s)["orders"]

    pipeline = {row["status"]: row["count"] for row in orders["open_by_status"]}
    assert (pipeline["AWAITING_PAYMENT"], pipeline["PENDING"], pipeline["PAID"]) == (7, 1, 0)
    assert len(orders["recent"]) == 5
    assert [o["id"] for o in orders["recent"][:3]] == [ids[0], pending_id, ids[1]]
    assert orders["recent"][0]["total"] == "13.00"


def test_other_organizations_never_leak_into_the_numbers(s: Scenario) -> None:
    other = make_scenario()
    other.stock(other.cola, 10)
    other.stock(other.water, 10)
    other.place()
    _payment(other, "500.00", NOW - timedelta(hours=1))

    data = _build(s)

    assert data["orders"]["submitted"]["value"] == 0
    assert data["orders"]["recent"] == []
    assert data["money"]["revenue"]["value"] == "0.00"


# Dinheiro --------------------------------------------------------------------------------------


def test_revenue_is_what_was_paid_minus_what_was_refunded_in_the_period(s: Scenario) -> None:
    _payment(s, "100.00", NOW - timedelta(hours=2))
    refunded = _payment(s, "40.00", NOW - timedelta(days=3), status="REFUNDED")
    _refund(s, refunded, NOW - timedelta(hours=1))  # pago há 3 dias, estornado hoje
    _payment(s, "999.00", NOW - timedelta(hours=1), status="DECLINED")
    _payment(s, "888.00", NOW - timedelta(hours=1), status="PENDING")
    _payment(s, "30.00", NOW - timedelta(days=1, hours=2))  # ontem, antes das 15:30

    money = _build(s)["money"]

    assert money["revenue"] == {"value": "60.00", "previous": "30.00"}  # 100 - 40
    assert money["refunded"]["value"] == "40.00"
    assert money["paid_orders"] == {"value": 1, "previous": 1}
    assert money["average_ticket"] == {"value": "100.00", "previous": "30.00"}
    assert sum(Decimal(slot["net"]) for slot in money["series"]) == Decimal("60.00")
    # Em 7 dias o pagamento estornado também entrou (na data em que foi pago): 100+40+30-40.
    assert _build(s, "7d")["money"]["revenue"]["value"] == "130.00"


def test_average_ticket_is_empty_without_payments(s: Scenario) -> None:
    assert _build(s)["money"]["average_ticket"] == {"value": None, "previous": None}


def test_counts_items_at_or_below_the_reorder_point(s: Scenario) -> None:
    StockItem.objects.filter(product=s.cola).update(reorder_point=50)  # 50 disponíveis: no ponto
    StockItem.objects.filter(product=s.water).update(reorder_point=49)

    assert _build(s)["stock"] == {"low_stock_items": 1}


# API, permissões e cache -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("role", "money", "stock"),
    [
        (Role.ADMIN, True, True),
        (Role.MANAGER, True, True),
        (Role.FINANCE, True, False),  # sem inventory:read
        (Role.SALES, False, True),
        (Role.WAREHOUSE, False, True),
        (Role.VIEWER, False, True),
    ],
)
def test_each_role_sees_only_what_its_permissions_allow(
    s: Scenario, role: Role, money: bool, stock: bool
) -> None:
    client = authenticated_client(make_user(role=role, organization=s.user.organization))

    body = client.get(URL, {"period": "7d"}).json()

    assert (body["money"] is not None, body["stock"] is not None) == (money, stock)
    assert body["orders"]["submitted"] is not None
    assert body["period"] == "7d"


def test_rejects_an_unknown_period(s: Scenario) -> None:
    response = s.client.get(URL, {"period": "1y"})

    assert response.status_code == 400


def test_defaults_to_the_last_7_days(s: Scenario) -> None:
    assert s.client.get(URL).json()["period"] == "7d"


@override_settings(DASHBOARD_CACHE_SECONDS=60)
def test_numbers_are_cached_per_organization_and_period_for_a_minute(s: Scenario) -> None:
    cache.clear()
    first = s.client.get(URL, {"period": "today"}).json()
    s.place()  # pedido novo depois do primeiro cálculo
    cached = s.client.get(URL, {"period": "today"}).json()
    other_period = s.client.get(URL, {"period": "7d"}).json()

    assert cached["orders"]["submitted"] == first["orders"]["submitted"]
    assert cached["generated_at"] == first["generated_at"]  # a tela mostra "atualizado às"
    assert other_period["orders"]["submitted"]["value"] == first["orders"]["submitted"]["value"] + 1


@override_settings(DASHBOARD_CACHE_SECONDS=60)
def test_the_shared_cache_never_leaks_money_to_who_cannot_see_it(s: Scenario) -> None:
    cache.clear()
    seller = authenticated_client(make_user(role=Role.SALES, organization=s.user.organization))

    s.client.get(URL)  # gerente preenche o cache (com dinheiro)
    body = seller.get(URL).json()

    assert body["money"] is None


@override_settings(DASHBOARD_CACHE_SECONDS=60)
def test_the_cache_is_per_organization(s: Scenario) -> None:
    cache.clear()
    other = make_scenario(role=Role.MANAGER)
    s.place()

    s.client.get(URL, {"period": "today"})
    body = other.client.get(URL, {"period": "today"}).json()

    assert body["orders"]["submitted"]["value"] == 0


def test_requires_authentication() -> None:
    from rest_framework.test import APIClient

    assert APIClient().get(URL).status_code == 401


def test_api_counts_an_order_placed_now(s: Scenario) -> None:
    cache.clear()
    s.place()

    body = s.client.get(URL, {"period": "today"}).json()

    assert body["orders"]["submitted"]["value"] == 1
    assert timezone.now() - datetime.fromisoformat(body["generated_at"]) < timedelta(minutes=1)
