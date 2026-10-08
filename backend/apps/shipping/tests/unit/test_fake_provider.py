from datetime import timedelta
from uuid import uuid4

import pytest
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone

from apps.shipping.domain.provider import Destination
from apps.shipping.infrastructure.fake_provider import FakeShippingProvider

DESTINATION = Destination(postal_code="01310100", city="São Paulo", state="SP")


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    cache.clear()


def test_the_same_key_always_returns_the_same_label() -> None:
    provider, key = FakeShippingProvider(), uuid4()

    first = provider.create_shipment(idempotency_key=key, reference="#1", destination=DESTINATION)
    again = provider.create_shipment(idempotency_key=key, reference="#1", destination=DESTINATION)
    other = provider.create_shipment(
        idempotency_key=uuid4(), reference="#2", destination=DESTINATION
    )

    assert first == again
    assert other.tracking_code != first.tracking_code


@override_settings(FAKE_SHIPPING_TRANSIT_MINUTES=30)
def test_delivers_after_the_transit_time() -> None:
    provider = FakeShippingProvider()
    label = provider.create_shipment(
        idempotency_key=uuid4(), reference="#1", destination=DESTINATION
    )

    assert provider.track(tracking_code=label.tracking_code).delivered_at is None
    cache.set(f"fakeship:created:{label.tracking_code}", timezone.now() - timedelta(minutes=31))
    assert provider.track(tracking_code=label.tracking_code).delivered_at is not None


@override_settings(FAKE_SHIPPING_TRANSIT_MINUTES=30)
def test_asking_again_for_the_label_does_not_restart_the_transit() -> None:
    provider, key = FakeShippingProvider(), uuid4()
    label = provider.create_shipment(idempotency_key=key, reference="#1", destination=DESTINATION)
    cache.set(f"fakeship:created:{label.tracking_code}", timezone.now() - timedelta(minutes=31))

    provider.create_shipment(idempotency_key=key, reference="#1", destination=DESTINATION)

    assert provider.track(tracking_code=label.tracking_code).delivered_at is not None


def test_an_unknown_tracking_code_is_still_in_transit() -> None:
    assert FakeShippingProvider().track(tracking_code="NOPE").delivered_at is None
