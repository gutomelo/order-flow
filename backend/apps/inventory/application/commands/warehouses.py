import re
from uuid import UUID

import structlog
from django.db import IntegrityError, transaction
from django.db.models import Q

from apps.inventory.domain.exceptions import (
    InvalidWarehouseCode,
    WarehouseCodeAlreadyInUse,
    WarehouseHasStock,
)
from apps.inventory.models import WAREHOUSE_CODE_PATTERN, StockItem, Warehouse

logger = structlog.get_logger(__name__)

_CODE = re.compile(WAREHOUSE_CODE_PATTERN)


def _normalize_code(raw: str) -> str:
    code = raw.strip().upper()
    if not _CODE.fullmatch(code):  # W1
        raise InvalidWarehouseCode(details={"field": "code"})
    return code


def create_warehouse(organization_id: UUID, *, code: str, name: str) -> Warehouse:
    try:
        with transaction.atomic():
            return Warehouse.objects.create(
                organization_id=organization_id, code=_normalize_code(code), name=name.strip()
            )
    except IntegrityError as exc:
        raise WarehouseCodeAlreadyInUse(details={"field": "code"}) from exc


def rename_warehouse(warehouse: Warehouse, *, name: str) -> Warehouse:
    # O código identifica o depósito em etiquetas e integrações: não muda depois de criado.
    warehouse.name = name.strip()
    warehouse.save(update_fields=["name", "updated_at"])
    return warehouse


def set_warehouse_active(warehouse: Warehouse, *, is_active: bool) -> Warehouse:
    with transaction.atomic():
        # FOR UPDATE no depósito: espera as movimentações em andamento (que têm FOR SHARE) e
        # impede novas até concluir — o saldo verificado abaixo não muda durante a inativação.
        warehouse = Warehouse.objects.select_for_update().get(id=warehouse.id)
        if warehouse.is_active == is_active:
            return warehouse
        if not is_active and (
            StockItem.objects.filter(warehouse=warehouse)
            .filter(Q(on_hand__gt=0) | Q(reserved__gt=0))
            .exists()
        ):  # W3
            raise WarehouseHasStock()
        warehouse.is_active = is_active
        warehouse.save(update_fields=["is_active", "updated_at"])
    logger.info(
        "inventory.warehouse.activated" if is_active else "inventory.warehouse.deactivated",
        warehouse_id=str(warehouse.id),
    )
    return warehouse
