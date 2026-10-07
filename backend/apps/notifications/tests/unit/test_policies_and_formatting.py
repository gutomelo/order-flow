from datetime import UTC, datetime
from decimal import Decimal

import pytest
from django.test import override_settings

from apps.inventory.domain.stock import crossed_reorder_point
from apps.notifications.application.formatting import local_datetime, money
from apps.notifications.domain.kinds import NotificationKind as K
from apps.notifications.domain.policies import mask_email, order_notification_kind


@pytest.mark.parametrize(
    ("from_status", "to_status", "kind"),
    [
        ("PENDING", "AWAITING_PAYMENT", K.ORDER_CONFIRMED),
        ("AWAITING_PAYMENT", "PAID", K.ORDER_PAID),
        ("READY_TO_SHIP", "SHIPPED", K.ORDER_SHIPPED),
        ("SHIPPED", "DELIVERED", K.ORDER_DELIVERED),
        ("PAID", "CANCELLED", K.ORDER_CANCELLED),
        ("PENDING", "CANCELLED", K.ORDER_CANCELLED),
        ("CANCELLED", "REFUNDED", K.ORDER_REFUNDED),
        # Sem aviso ao cliente:
        ("DRAFT", "CANCELLED", None),  # rascunho nunca chegou ao cliente
        (None, "DRAFT", None),
        (None, "PENDING", None),  # sem estoque: avisa quando reservar
        ("AWAITING_PAYMENT", "PENDING", None),  # reserva expirou
        ("PAID", "PROCESSING", None),  # separação é interna
        ("PROCESSING", "READY_TO_SHIP", None),
    ],
)
def test_which_order_changes_reach_the_customer(
    from_status: str | None, to_status: str, kind: K | None
) -> None:
    assert order_notification_kind(from_status, to_status) == kind


@pytest.mark.parametrize(
    ("email", "masked"),
    [("maria@empresa.com", "ma***@empresa.com"), ("a@b.com", "a***@b.com"), ("bad", "***")],
)
def test_masks_the_recipient(email: str, masked: str) -> None:
    assert mask_email(email) == masked


@pytest.mark.parametrize(
    ("value", "text"),
    [("13.00", "R$ 13,00"), ("1234.5", "R$ 1.234,50"), ("1234567.89", "R$ 1.234.567,89")],
)
def test_formats_money_in_brazilian_portuguese(value: str, text: str) -> None:
    assert money(Decimal(value)) == text


@override_settings(NOTIFICATIONS_TIME_ZONE="America/Sao_Paulo")
def test_formats_dates_in_the_configured_time_zone() -> None:
    assert local_datetime(datetime(2026, 10, 8, 15, 30, tzinfo=UTC)) == "08/10/2026 às 12:30"


@pytest.mark.parametrize(
    ("before", "after", "reorder_point", "crossed"),
    [
        (10, 8, 9, True),  # cruzou
        (10, 9, 9, True),  # chegou exatamente no ponto
        (9, 8, 9, False),  # já estava baixo: sem novo aviso
        (8, 12, 9, False),  # subiu
        (10, 2, 0, False),  # ponto zero desliga o alerta
    ],
)
def test_low_stock_fires_only_when_crossing_the_reorder_point(
    before: int, after: int, reorder_point: int, crossed: bool
) -> None:
    assert crossed_reorder_point(before, after, reorder_point) is crossed
