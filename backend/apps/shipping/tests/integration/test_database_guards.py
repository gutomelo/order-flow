"""O banco protege a remessa mesmo contra código que contorne os serviços."""

from typing import Any
from uuid import uuid4

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.identity.tests.factories import make_user
from apps.shipping.models import Shipment

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _shipment(user: Any, **kwargs: Any) -> Shipment:
    values: dict[str, Any] = {
        "order_id": uuid4(),
        "order_reference": "#000001",
        "carrier": "Transportadora Simulada",
        "tracking_code": f"SIM{uuid4().hex[:8]}",
        "status": "IN_TRANSIT",
        "shipped_at": timezone.now(),
        **kwargs,
    }
    return Shipment.objects.create(organization_id=user.organization_id, shipped_by=user, **values)


def test_an_order_has_a_single_shipment() -> None:  # S1
    user, order_id = make_user(), uuid4()
    _shipment(user, order_id=order_id)

    with pytest.raises(IntegrityError), transaction.atomic():
        _shipment(user, order_id=order_id)


def test_a_tracking_code_is_unique_per_carrier() -> None:
    user = make_user()
    _shipment(user, tracking_code="SIM1")

    with pytest.raises(IntegrityError), transaction.atomic():
        _shipment(user, tracking_code="SIM1")


@pytest.mark.parametrize(
    "fields",
    [
        {"status": "DELIVERED"},  # entregue sem data nem origem
        {"status": "DELIVERED", "delivered_at": timezone.now()},  # sem origem
        {"status": "IN_TRANSIT", "delivered_at": timezone.now(), "delivery_source": "MANUAL"},
        {"status": "LOST"},
    ],
)
def test_delivery_fields_follow_the_status(fields: dict[str, Any]) -> None:  # S3
    with pytest.raises(IntegrityError), transaction.atomic():
        _shipment(make_user(), **fields)
