"""Cenários de concorrência de estoque (ADR-008, docs/development/testing-strategy.md T3/T4).

Cada thread usa sua própria conexão (`transaction=True`); barreiras alinham o início das
transações para que elas realmente disputem as mesmas linhas.
"""

import threading
import time
from collections.abc import Callable
from typing import Any

import pytest
from django.db import connection

from apps.catalog.tests.factories import make_product
from apps.identity.domain.permissions import Role
from apps.identity.tests.factories import make_user
from apps.inventory.application import ledger
from apps.inventory.application.commands.receive_stock import (
    ReceiptLine,
    ReceiveStock,
    ReceiveStockCommand,
)
from apps.inventory.application.commands.transfer_stock import (
    TransferStock,
    TransferStockCommand,
)
from apps.inventory.application.commands.warehouses import set_warehouse_active
from apps.inventory.domain.exceptions import InsufficientStock, WarehouseHasStock
from apps.inventory.models import StockItem, StockMovement, Warehouse
from apps.inventory.tests.factories import make_stock_item, make_warehouse

pytestmark = [pytest.mark.concurrency, pytest.mark.django_db(transaction=True)]


def _run_concurrently(*tasks: Callable[[], str]) -> list[str]:
    barrier = threading.Barrier(len(tasks))
    outcomes: list[str] = []

    def runner(task: Callable[[], str]) -> None:
        try:
            barrier.wait()
            outcomes.append(task())
        except Exception as exc:
            outcomes.append(type(exc).__name__)
        finally:
            connection.close()

    threads = [threading.Thread(target=runner, args=(task,)) for task in tasks]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return outcomes


def _transfer(item: StockItem, to: Warehouse, quantity: int, actor_id: Any) -> Callable[[], str]:
    def task() -> str:
        TransferStock().execute(
            TransferStockCommand(
                organization_id=item.organization_id,
                actor_id=actor_id,
                stock_item_id=item.id,
                to_warehouse_id=to.id,
                quantity=quantity,
            )
        )
        return "ok"

    return task


def test_the_last_unit_is_never_moved_twice() -> None:
    user = make_user(role=Role.WAREHOUSE)
    origin = make_warehouse(organization=user.organization)
    destination_a = make_warehouse(organization=user.organization)
    destination_b = make_warehouse(organization=user.organization)
    item = make_stock_item(warehouse=origin, on_hand=1)

    outcomes = _run_concurrently(
        _transfer(item, destination_a, 1, user.id), _transfer(item, destination_b, 1, user.id)
    )

    assert sorted(outcomes) == [InsufficientStock.__name__, "ok"]
    item.refresh_from_db()
    assert item.on_hand == 0
    assert (
        sum(StockItem.objects.filter(product=item.product).values_list("on_hand", flat=True)) == 1
    )


def test_opposite_transfers_do_not_deadlock() -> None:
    user = make_user(role=Role.WAREHOUSE)
    sp = make_warehouse(organization=user.organization)
    rj = make_warehouse(organization=user.organization)
    product = make_product(organization=user.organization)
    in_sp = make_stock_item(warehouse=sp, product=product, on_hand=10)
    in_rj = make_stock_item(warehouse=rj, product=product, on_hand=10)

    outcomes = _run_concurrently(_transfer(in_sp, rj, 3, user.id), _transfer(in_rj, sp, 5, user.id))

    assert outcomes == ["ok", "ok"]
    in_sp.refresh_from_db()
    in_rj.refresh_from_db()
    assert (in_sp.on_hand, in_rj.on_hand) == (12, 8)


def test_concurrent_first_receipts_share_a_single_stock_item() -> None:
    user = make_user(role=Role.WAREHOUSE)
    warehouse = make_warehouse(organization=user.organization)
    product = make_product(organization=user.organization)

    def receive(quantity: int) -> Callable[[], str]:
        def task() -> str:
            ReceiveStock().execute(
                ReceiveStockCommand(
                    organization_id=user.organization_id,  # type: ignore[arg-type]
                    actor_id=user.id,
                    warehouse_id=warehouse.id,
                    lines=(ReceiptLine(product_id=product.id, quantity=quantity),),
                )
            )
            return "ok"

        return task

    outcomes = _run_concurrently(receive(4), receive(6))

    assert outcomes == ["ok", "ok"]
    item = StockItem.objects.get(product=product, warehouse=warehouse)
    assert item.on_hand == 10
    assert sorted(item.movements.values_list("on_hand_after", flat=True)) == [4, 10] or sorted(
        item.movements.values_list("on_hand_after", flat=True)
    ) == [6, 10]


def test_warehouse_cannot_be_deactivated_while_a_receipt_is_in_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sem o FOR SHARE no depósito, a inativação veria "saldo zero" e o recebimento gravaria
    estoque em um depósito inativo logo depois."""
    user = make_user(role=Role.WAREHOUSE)
    warehouse = make_warehouse(organization=user.organization)
    product = make_product(organization=user.organization)
    receipt_holds_lock = threading.Event()

    original = ledger.lock_warehouses_for_movement

    def lock_then_pause(*args: Any, **kwargs: Any) -> None:
        original(*args, **kwargs)
        receipt_holds_lock.set()
        time.sleep(0.5)  # recebimento ainda em andamento, depósito já verificado

    monkeypatch.setattr(
        "apps.inventory.application.commands.receive_stock.lock_warehouses_for_movement",
        lock_then_pause,
    )

    def receive() -> str:
        ReceiveStock().execute(
            ReceiveStockCommand(
                organization_id=user.organization_id,  # type: ignore[arg-type]
                actor_id=user.id,
                warehouse_id=warehouse.id,
                lines=(ReceiptLine(product_id=product.id, quantity=5),),
            )
        )
        return "received"

    def deactivate() -> str:
        receipt_holds_lock.wait(timeout=5)
        set_warehouse_active(Warehouse.objects.get(id=warehouse.id), is_active=False)
        return "deactivated"

    outcomes = _run_concurrently(receive, deactivate)

    assert sorted(outcomes) == [WarehouseHasStock.__name__, "received"]
    warehouse.refresh_from_db()
    assert warehouse.is_active is True
    assert StockMovement.objects.filter(stock_item__warehouse=warehouse).count() == 1
