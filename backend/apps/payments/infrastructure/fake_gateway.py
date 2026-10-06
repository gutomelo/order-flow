"""Gateway simulado (dev/teste/demonstração). O comportamento vem do token de teste.

O "lado do provedor" (cobranças já processadas) fica no cache — Redis em dev, compartilhado entre
API e worker —, como um provedor real que lembra o que processou pela chave de idempotência.
"""

from decimal import Decimal
from uuid import UUID

from django.core.cache import cache

from apps.payments.domain.gateway import ChargeResult, GatewayUnavailable, RefundResult

# Comportamento simulado por token de teste (docs/domain/payments.md#gateway).
BEHAVIORS: dict[str, str] = {
    "tok_approved": "approve",
    "tok_declined": "decline",
    "tok_timeout": "approve_then_timeout",
    "tok_unavailable": "unavailable",
    "tok_refund_fails": "approve_refund_fails",
}
_TTL = 60 * 60 * 24 * 30


class FakePaymentGateway:
    def charge(
        self, *, idempotency_key: UUID, amount: Decimal, currency: str, card_token: str
    ) -> ChargeResult:
        existing = self.get_charge(idempotency_key=idempotency_key)
        if existing is not None:  # idempotência do provedor: mesma chave, mesmo resultado
            return existing
        behavior = BEHAVIORS.get(card_token, "approve")
        if behavior == "unavailable":
            raise GatewayUnavailable("fake: provedor indisponível, nada cobrado")
        reference = f"fake_ch_{idempotency_key.hex}"
        result = (
            ChargeResult("DECLINED", reference, "insufficient_funds")
            if behavior == "decline"
            else ChargeResult("APPROVED", reference)
        )
        cache.set(f"fakegw:charge:{idempotency_key}", result, _TTL)
        cache.set(f"fakegw:refund_fails:{reference}", behavior == "approve_refund_fails", _TTL)
        if behavior == "approve_then_timeout":
            # O provedor processou, mas a resposta se perdeu: só a reconciliação descobre.
            raise GatewayUnavailable("fake: timeout depois de processar")
        return result

    def get_charge(self, *, idempotency_key: UUID) -> ChargeResult | None:
        result: ChargeResult | None = cache.get(f"fakegw:charge:{idempotency_key}")
        return result

    def refund(
        self, *, idempotency_key: UUID, provider_reference: str, amount: Decimal
    ) -> RefundResult:
        reference = f"fake_re_{idempotency_key.hex}"
        if cache.get(f"fakegw:refund_fails:{provider_reference}"):
            return RefundResult("FAILED", reference, "refund_rejected")
        return RefundResult("SUCCEEDED", reference)
