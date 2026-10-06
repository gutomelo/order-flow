"""Porta do gateway de pagamento (DIP): o domínio define, a infraestrutura implementa.

Toda chamada carrega uma chave de idempotência do NOSSO registro (pagamento/estorno): repetir a
chamada após um timeout nunca cobra ou estorna duas vezes.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Protocol
from uuid import UUID


class GatewayUnavailable(Exception):
    """Sem resposta conclusiva (timeout, 5xx, conexão): o resultado é desconhecido."""


@dataclass(frozen=True)
class ChargeResult:
    status: Literal["APPROVED", "DECLINED"]
    provider_reference: str
    decline_reason: str = ""


@dataclass(frozen=True)
class RefundResult:
    status: Literal["SUCCEEDED", "FAILED"]
    provider_reference: str
    failure_reason: str = ""


class PaymentGateway(Protocol):
    def charge(
        self, *, idempotency_key: UUID, amount: Decimal, currency: str, card_token: str
    ) -> ChargeResult: ...

    def get_charge(self, *, idempotency_key: UUID) -> ChargeResult | None:
        """Consulta de reconciliação; `None` = o provedor não tem registro dessa cobrança."""
        ...

    def refund(
        self, *, idempotency_key: UUID, provider_reference: str, amount: Decimal
    ) -> RefundResult: ...
