"""O banco protege o dinheiro mesmo contra código que contorne os serviços."""

from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from django.db import IntegrityError, transaction

from apps.identity.tests.factories import make_user
from apps.payments.models import Payment

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _payment(user: Any, order_id: Any, **kwargs: Any) -> Payment:
    values: dict[str, Any] = {
        "method": "CARD",
        "status": "APPROVED",
        "amount": Decimal("10.00"),
        "order_reference": "#000001",
        **kwargs,
    }
    return Payment.objects.create(
        organization_id=user.organization_id, order_id=order_id, created_by=user, **values
    )


def test_an_order_is_never_approved_twice() -> None:  # P1
    user, order_id = make_user(), uuid4()
    _payment(user, order_id)
    _payment(user, order_id, status="DECLINED")  # recusadas não contam

    with pytest.raises(IntegrityError), transaction.atomic():
        _payment(user, order_id)


def test_one_charge_in_flight_per_order() -> None:  # P2
    user, order_id = make_user(), uuid4()
    _payment(user, order_id, status="PENDING")

    with pytest.raises(IntegrityError), transaction.atomic():
        _payment(user, order_id, status="PENDING")


@pytest.mark.parametrize(
    "fields", [{"amount": Decimal("0")}, {"method": "MANUAL", "manual_reference": ""}]
)
def test_amount_and_manual_reference_are_enforced(fields: dict[str, Any]) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        _payment(make_user(), uuid4(), **fields)
