"""Único ponto de escrita de saldo de estoque (ADR-008, docs/domain/inventory.md).

Todo caso de uso que altera `on_hand`/`reserved` usa estas funções dentro de `transaction.atomic()`:

1. `lock_warehouses_for_movement` — lock compartilhado nos depósitos (barra inativação concorrente);
2. `ensure_stock_items` — cria itens ausentes sem corrida (`ON CONFLICT DO NOTHING`);
3. `lock_stock_items` — `SELECT ... FOR UPDATE` em ordem de `id` (evita deadlock);
4. `post_movement` — aplica a regra do domínio, grava o saldo e o `StockMovement` juntos.

Ordem global de locks: depósito → itens de estoque (por id).
"""

from collections.abc import Iterable, Sequence
from uuid import UUID

from django.db import connection

from apps.inventory.domain.events import StockChanged, StockLevelLow
from apps.inventory.domain.exceptions import WarehouseInactive, WarehouseNotFound
from apps.inventory.domain.movements import MovementType
from apps.inventory.domain.stock import StockBalance, crossed_reorder_point
from apps.inventory.models import StockItem, StockMovement
from shared.events.bus import publish
from shared.logging import get_request_id


def lock_warehouses_for_movement(organization_id: UUID, warehouse_ids: Sequence[UUID]) -> None:
    """`FOR SHARE` nos depósitos e verificação de que estão ativos (regra W2).

    Movimentações no mesmo depósito não se bloqueiam entre si (lock compartilhado), mas a
    inativação (`FOR UPDATE`) espera todas terminarem — e vice-versa —, então nenhum saldo
    entra em um depósito no meio da sua inativação (regra W3).

    SQL manual justificado: o ORM do Django não expõe `FOR SHARE`. Consulta parametrizada.
    """
    ids = sorted(set(warehouse_ids))
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, is_active FROM inventory_warehouse "
            "WHERE organization_id = %s AND id = ANY(%s) ORDER BY id FOR SHARE",
            [organization_id, ids],
        )
        rows = dict(cursor.fetchall())
    for warehouse_id in ids:
        if warehouse_id not in rows:
            raise WarehouseNotFound(details={"warehouse_id": str(warehouse_id)})
        if not rows[warehouse_id]:
            raise WarehouseInactive(details={"warehouse_id": str(warehouse_id)})


def ensure_stock_items(organization_id: UUID, pairs: Iterable[tuple[UUID, UUID]]) -> None:
    """Cria os itens (produto, depósito) ausentes com saldo zero.

    `INSERT ... ON CONFLICT DO NOTHING`: dois recebimentos simultâneos do mesmo produto novo não
    criam dois itens nem falham — o segundo espera o primeiro e segue com o item existente.
    """
    StockItem.objects.bulk_create(
        [
            StockItem(organization_id=organization_id, product_id=product, warehouse_id=warehouse)
            for product, warehouse in pairs
        ],
        ignore_conflicts=True,
    )


def lock_stock_items(organization_id: UUID, **filters: object) -> list[StockItem]:
    return list(
        StockItem.objects.for_organization(organization_id)
        .select_for_update(of=("self",))
        .select_related("warehouse")
        .filter(**filters)
        .order_by("id")
    )


# Movimentos feitos por uma pessoa: entram na auditoria (os do pedido são auditados pelo pedido).
MANUAL_MOVEMENTS = frozenset(
    {MovementType.PURCHASE, MovementType.ADJUSTMENT, MovementType.TRANSFER}
)


def post_movement(
    item: StockItem,
    movement_type: MovementType,
    *,
    on_hand_delta: int,
    reserved_delta: int = 0,
    actor_id: UUID | None,
    reference_type: str = "",
    reference_id: UUID | None = None,
    reason: str = "",
) -> StockMovement:
    """Aplica o delta ao item (já bloqueado) e registra o movimento na mesma transação.

    Se o disponível cruza o ponto de reposição para baixo, publica `inventory.stock.low` na mesma
    transação (outbox): rollback do movimento desfaz o aviso.
    """
    before = StockBalance(item.on_hand, item.reserved)
    balance = before.apply(on_hand_delta=on_hand_delta, reserved_delta=reserved_delta)
    # Com a linha bloqueada, gravar o valor resultante é seguro e mantém `*_after` coerente.
    item.on_hand, item.reserved = balance.on_hand, balance.reserved
    item.save(update_fields=["on_hand", "reserved", "updated_at"])
    if crossed_reorder_point(before.available, balance.available, item.reorder_point):
        publish(
            StockLevelLow(
                organization_id=item.organization_id,
                stock_item_id=item.id,
                available=balance.available,
                reorder_point=item.reorder_point,
            )
        )
    movement = StockMovement.objects.create(
        organization_id=item.organization_id,
        stock_item=item,
        type=movement_type,
        on_hand_delta=on_hand_delta,
        reserved_delta=reserved_delta,
        on_hand_after=balance.on_hand,
        reserved_after=balance.reserved,
        reference_type=reference_type,
        reference_id=reference_id,
        reason=reason,
        performed_by_id=actor_id,
        request_id=get_request_id() or "",
    )
    if movement_type in MANUAL_MOVEMENTS:
        publish(
            StockChanged(
                organization_id=item.organization_id,
                stock_item_id=item.id,
                movement_id=movement.id,
                movement_type=movement_type.value,
                on_hand_before=before.on_hand,
                on_hand_after=balance.on_hand,
                reserved_before=before.reserved,
                reserved_after=balance.reserved,
                actor_id=actor_id,
                reason=reason,
            )
        )
    return movement
