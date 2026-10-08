"""Porta da transportadora (DIP): o domínio define, a infraestrutura implementa.

`create_shipment` recebe a chave de idempotência da remessa (o id do pedido: uma remessa por
pedido, S1). Repetir a chamada após um timeout devolve a mesma etiqueta, nunca uma segunda.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


class ProviderUnavailable(Exception):
    """Sem resposta conclusiva da transportadora (timeout, 5xx, conexão)."""


@dataclass(frozen=True)
class Destination:
    postal_code: str
    city: str
    state: str


@dataclass(frozen=True)
class Label:
    carrier: str
    tracking_code: str


@dataclass(frozen=True)
class Tracking:
    delivered_at: datetime | None  # `None` = ainda em trânsito


class ShippingProvider(Protocol):
    def create_shipment(
        self, *, idempotency_key: UUID, reference: str, destination: Destination
    ) -> Label: ...

    def track(self, *, tracking_code: str) -> Tracking: ...
