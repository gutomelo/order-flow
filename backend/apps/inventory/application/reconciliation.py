"""Reconciliação de saldos (I6, I7 em docs/domain/inventory.md).

As duas invariantes não cabem num CHECK: dependem de somar outras tabelas. O job compara e
**alerta**; nunca corrige sozinho — uma divergência é sintoma de bug e precisa de análise.
"""

from dataclasses import dataclass
from uuid import UUID

from django.db.models import F, IntegerField, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from apps.inventory.domain.reservations import HOLDING
from apps.inventory.models import StockItem, StockMovement, StockReservation


@dataclass(frozen=True)
class Divergence:
    stock_item_id: UUID
    field: str
    stored: int
    expected: int


def find_divergences() -> list[Divergence]:
    holding = (
        StockReservation.objects.filter(stock_item=OuterRef("pk"), status__in=list(HOLDING))
        .values("stock_item")
        .annotate(total=Sum("quantity"))
        .values("total")
    )
    moved = (
        StockMovement.objects.filter(stock_item=OuterRef("pk"))
        .values("stock_item")
        .annotate(total=Sum("on_hand_delta"))
        .values("total")
    )
    items = StockItem.objects.annotate(
        expected_reserved=Coalesce(Subquery(holding, output_field=IntegerField()), Value(0)),
        expected_on_hand=Coalesce(Subquery(moved, output_field=IntegerField()), Value(0)),
    ).filter(~Q(reserved=F("expected_reserved")) | ~Q(on_hand=F("expected_on_hand")))

    found: list[Divergence] = []
    for item in items:
        if item.reserved != item.expected_reserved:  # I6
            found.append(Divergence(item.id, "reserved", item.reserved, item.expected_reserved))
        if item.on_hand != item.expected_on_hand:  # I7
            found.append(Divergence(item.id, "on_hand", item.on_hand, item.expected_on_hand))
    return found
