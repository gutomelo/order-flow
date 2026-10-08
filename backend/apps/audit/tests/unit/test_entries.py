from uuid import uuid4

import pytest

from apps.audit.domain.entries import (
    AuditAction as A,
)
from apps.audit.domain.entries import (
    from_order_status,
    from_payment_status,
    from_refund_status,
    from_stock_change,
)

ORDER = str(uuid4())


def _order(source: str | None, target: str) -> dict[str, object]:
    return {
        "order_id": ORDER,
        "from_status": source,
        "to_status": target,
        "actor_id": None,
        "reason": "",
    }


@pytest.mark.parametrize(
    ("source", "target", "action"),
    [
        (None, "PENDING", A.ORDER_CREATED),
        (None, "DRAFT", A.ORDER_CREATED),
        ("PENDING", "AWAITING_PAYMENT", A.ORDER_STATUS_CHANGED),
        ("PAID", "CANCELLED", A.ORDER_CANCELLED),
        ("CANCELLED", "REFUNDED", A.ORDER_STATUS_CHANGED),
    ],
)
def test_order_transitions(source: str | None, target: str, action: A) -> None:
    entry = from_order_status(_order(source, target))

    assert entry.action == action
    assert entry.changes == {"status": [source, target]}
    assert str(entry.order_id) == ORDER


@pytest.mark.parametrize(
    ("source", "target", "action"),
    [
        (None, "PENDING", A.PAYMENT_STARTED),
        (None, "APPROVED", A.PAYMENT_RECORDED),
        ("PENDING", "APPROVED", A.PAYMENT_APPROVED),
        ("PENDING", "DECLINED", A.PAYMENT_DECLINED),
        ("PENDING", "FAILED", A.PAYMENT_FAILED),
        ("APPROVED", "REFUNDED", A.PAYMENT_REFUNDED),
    ],
)
def test_payment_transitions(source: str | None, target: str, action: A) -> None:
    payload = {
        "payment_id": str(uuid4()),
        "order_id": ORDER,
        "from_status": source,
        "to_status": target,
        "actor_id": str(uuid4()),
        "note": "insufficient_funds",
        "amount": "13.00",
        "method": "CARD",
    }

    entry = from_payment_status(payload)

    assert entry.action == action
    assert entry.changes["amount"] == "13.00"
    assert entry.reason == "insufficient_funds"


@pytest.mark.parametrize(
    ("source", "target", "action"),
    [
        (None, "PENDING", A.REFUND_REQUESTED),
        ("FAILED", "PENDING", A.REFUND_RETRIED),
        ("PENDING", "SUCCEEDED", A.REFUND_COMPLETED),
        ("PENDING", "FAILED", A.REFUND_FAILED),
    ],
)
def test_refund_transitions(source: str | None, target: str, action: A) -> None:
    payload = {
        "refund_id": str(uuid4()),
        "order_id": ORDER,
        "from_status": source,
        "to_status": target,
        "actor_id": None,
        "note": "",
        "amount": "13.00",
    }

    assert from_refund_status(payload).action == action


def test_stock_change_shows_reserved_only_when_it_moved() -> None:
    base = {
        "stock_item_id": str(uuid4()),
        "movement_type": "ADJUSTMENT",
        "on_hand_before": 10,
        "on_hand_after": 7,
        "reserved_before": 2,
        "reserved_after": 2,
        "actor_id": None,
        "reason": "Quebra",
    }

    entry = from_stock_change(base)

    assert (entry.action, entry.changes) == (A.STOCK_ADJUSTED, {"on_hand": [10, 7]})
