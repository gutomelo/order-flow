from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from apps.payments.domain.gateway import PaymentGateway
from apps.payments.infrastructure.fake_gateway import FakePaymentGateway


def get_payment_gateway() -> PaymentGateway:
    """Escolhe o adapter por configuração (Factory): sem `if` de ambiente espalhado."""
    if settings.PAYMENT_GATEWAY == "fake":
        return FakePaymentGateway()
    raise ImproperlyConfigured(f"PAYMENT_GATEWAY desconhecido: {settings.PAYMENT_GATEWAY!r}")
