"""Transportadora simulada (dev/teste). O "lado do provedor" fica no cache (Redis em dev).

A remessa é dada como entregue `FAKE_SHIPPING_TRANSIT_MINUTES` depois de criada: o rastreio do
Beat descobre isso como descobriria numa transportadora real.
"""

from datetime import datetime, timedelta
from uuid import UUID

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.shipping.domain.provider import Destination, Label, Tracking

CARRIER = "Transportadora Simulada"
_TTL = 60 * 60 * 24 * 30


class FakeShippingProvider:
    def create_shipment(
        self, *, idempotency_key: UUID, reference: str, destination: Destination
    ) -> Label:
        existing: Label | None = cache.get(f"fakeship:label:{idempotency_key}")
        if existing is not None:  # idempotência do provedor: mesma chave, mesma etiqueta
            return existing
        label = Label(carrier=CARRIER, tracking_code=f"SIM{idempotency_key.hex[:10].upper()}BR")
        cache.set(f"fakeship:label:{idempotency_key}", label, _TTL)
        cache.set(f"fakeship:created:{label.tracking_code}", timezone.now(), _TTL)
        return label

    def track(self, *, tracking_code: str) -> Tracking:
        created: datetime | None = cache.get(f"fakeship:created:{tracking_code}")
        if created is None:
            return Tracking(delivered_at=None)
        delivered_at = created + timedelta(minutes=settings.FAKE_SHIPPING_TRANSIT_MINUTES)
        return Tracking(delivered_at=delivered_at if delivered_at <= timezone.now() else None)
