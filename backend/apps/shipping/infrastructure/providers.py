from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from apps.shipping.domain.provider import ShippingProvider
from apps.shipping.infrastructure.fake_provider import FakeShippingProvider


def get_shipping_provider() -> ShippingProvider:
    """Escolhe o adapter por configuração (Factory): sem `if` de ambiente espalhado."""
    if settings.SHIPPING_PROVIDER == "fake":
        return FakeShippingProvider()
    raise ImproperlyConfigured(f"SHIPPING_PROVIDER desconhecido: {settings.SHIPPING_PROVIDER!r}")
