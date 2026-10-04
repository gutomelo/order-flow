"""Regras de escrita do catálogo (docs/domain/catalog.md).

Módulo de complexidade baixa/média: as regras cabem em serviços coesos (um por intenção) sem
justificar camadas `application/`/`domain/` separadas.
"""

import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import structlog
from django.db import IntegrityError, transaction

from apps.catalog.exceptions import (
    BarcodeAlreadyInUse,
    CategoryCycle,
    CategoryDepthExceeded,
    CategoryHasActiveChildren,
    CategoryNameAlreadyInUse,
    CategoryNotAvailable,
    InvalidBarcode,
    InvalidSku,
    ParentCategoryInactive,
    SkuAlreadyInUse,
    SupplierNotAvailable,
)
from apps.catalog.models import MAX_CATEGORY_DEPTH, SKU_PATTERN, Category, Product
from apps.catalog.selectors import descendant_ids
from apps.suppliers.models import Supplier
from apps.suppliers.selectors import get_active_supplier
from shared.domain.barcodes import is_valid_gtin
from shared.infrastructure.db import violated_constraint

logger = structlog.get_logger(__name__)

_SKU = re.compile(SKU_PATTERN)
_UNSET: Any = object()


# ---------------------------------------------------------------------------
# Produtos
# ---------------------------------------------------------------------------


def _normalize_sku(raw: str) -> str:
    sku = raw.strip().upper()
    if not _SKU.fullmatch(sku):  # C1
        raise InvalidSku(details={"field": "sku"})
    return sku


def _normalize_barcode(raw: str) -> str:
    barcode = raw.strip()
    if barcode and not is_valid_gtin(barcode):  # C3
        raise InvalidBarcode(details={"field": "barcode"})
    return barcode


def _available_category(organization_id: UUID, category_id: UUID | None) -> Category | None:
    if category_id is None:
        return None
    category = (
        Category.objects.for_organization(organization_id)
        .filter(id=category_id, is_active=True)
        .first()
    )
    if category is None:  # C4
        raise CategoryNotAvailable(details={"field": "category_id"})
    return category


def _available_supplier(organization_id: UUID, supplier_id: UUID | None) -> Supplier | None:
    if supplier_id is None:
        return None
    supplier = get_active_supplier(organization_id, supplier_id)
    if supplier is None:  # C4 / S4
        raise SupplierNotAvailable(details={"field": "default_supplier_id"})
    return supplier


def _save_product(product: Product) -> Product:
    try:
        with transaction.atomic():
            product.save()
    except IntegrityError as exc:
        # C2/C3: as UNIQUEs do banco decidem também em criações concorrentes.
        if violated_constraint(exc) == "catalog_product_org_barcode_uniq":
            raise BarcodeAlreadyInUse(details={"field": "barcode"}) from exc
        raise SkuAlreadyInUse(details={"field": "sku"}) from exc
    return product


@dataclass(frozen=True)
class ProductData:
    sku: str
    name: str
    description: str = ""
    unit: str = "UNIT"
    barcode: str = ""
    category_id: UUID | None = None
    default_supplier_id: UUID | None = None


def create_product(organization_id: UUID, data: ProductData) -> Product:
    product = Product(
        organization_id=organization_id,
        sku=_normalize_sku(data.sku),
        name=data.name.strip(),
        description=data.description.strip(),
        unit=data.unit,
        barcode=_normalize_barcode(data.barcode),
        category=_available_category(organization_id, data.category_id),
        default_supplier=_available_supplier(organization_id, data.default_supplier_id),
    )
    _save_product(product)
    logger.info("catalog.product.created", product_id=str(product.id), sku=product.sku)
    return product


def update_product(product: Product, changes: dict[str, Any]) -> Product:
    """Atualização parcial. SKU não é editável (C7) — a API não o aceita aqui."""
    organization_id = product.organization_id
    for name in ("name", "description"):
        if name in changes:
            setattr(product, name, changes[name].strip())
    if "unit" in changes:
        product.unit = changes["unit"]
    if "barcode" in changes:
        product.barcode = _normalize_barcode(changes["barcode"])
    if "category_id" in changes:
        product.category = _available_category(organization_id, changes["category_id"])
    if "default_supplier_id" in changes:
        product.default_supplier = _available_supplier(
            organization_id, changes["default_supplier_id"]
        )
    return _save_product(product)


def set_product_active(product: Product, *, is_active: bool) -> Product:
    # C6: inativação no lugar de exclusão; pedidos e estoque continuam referenciando o produto.
    if product.is_active != is_active:
        product.is_active = is_active
        product.save(update_fields=["is_active", "updated_at"])
        logger.info(
            "catalog.product.activated" if is_active else "catalog.product.deactivated",
            product_id=str(product.id),
        )
    return product


# ---------------------------------------------------------------------------
# Categorias
# ---------------------------------------------------------------------------


def _subtree_height(organization_id: UUID, category: Category) -> int:
    """Quantos níveis a subárvore ocupa abaixo da categoria (0 = sem filhos)."""
    deepest = max(
        (
            c.depth
            for c in Category.objects.for_organization(organization_id).filter(
                id__in=descendant_ids(organization_id, category.id)
            )
        ),
        default=category.depth,
    )
    return deepest - category.depth


def _resolve_parent(organization_id: UUID, parent_id: UUID | None) -> Category | None:
    if parent_id is None:
        return None
    parent = (
        Category.objects.for_organization(organization_id)
        .select_for_update()
        .filter(id=parent_id)
        .first()
    )
    if parent is None:
        raise CategoryNotAvailable(details={"field": "parent_id"})
    if not parent.is_active:  # K4
        raise ParentCategoryInactive(details={"field": "parent_id"})
    return parent


def _save_category(category: Category) -> Category:
    try:
        with transaction.atomic():
            category.save()
    except IntegrityError as exc:  # K3
        raise CategoryNameAlreadyInUse(details={"field": "name"}) from exc
    return category


def create_category(organization_id: UUID, *, name: str, parent_id: UUID | None) -> Category:
    with transaction.atomic():
        parent = _resolve_parent(organization_id, parent_id)
        depth = parent.depth + 1 if parent else 1
        if depth > MAX_CATEGORY_DEPTH:  # K1
            raise CategoryDepthExceeded(details={"field": "parent_id"})
        category = Category(
            organization_id=organization_id, name=name.strip(), parent=parent, depth=depth
        )
        return _save_category(category)


def update_category(
    category: Category, *, name: str | None = None, parent_id: Any = _UNSET
) -> Category:
    """Renomeia e/ou move a categoria (com toda a subárvore)."""
    organization_id = category.organization_id
    with transaction.atomic():
        # Lock da subárvore: movimentos concorrentes não podem deixar profundidades incoerentes.
        subtree = descendant_ids(organization_id, category.id)
        locked = {
            c.id: c
            for c in Category.objects.for_organization(organization_id)
            .select_for_update()
            .filter(id__in=subtree)
            .order_by("id")
        }
        category = locked[category.id]

        if name is not None:
            category.name = name.strip()

        if parent_id is not _UNSET and parent_id != category.parent_id:
            if parent_id is not None and parent_id in subtree:  # K2
                raise CategoryCycle(details={"field": "parent_id"})
            parent = _resolve_parent(organization_id, parent_id)
            new_depth = parent.depth + 1 if parent else 1
            height = _subtree_height(organization_id, category)
            if new_depth + height > MAX_CATEGORY_DEPTH:  # K1
                raise CategoryDepthExceeded(details={"field": "parent_id"})
            shift = new_depth - category.depth
            category.parent = parent
            category.depth = new_depth
            for descendant in locked.values():
                if descendant.id != category.id and shift:
                    descendant.depth += shift
                    descendant.save(update_fields=["depth", "updated_at"])

        return _save_category(category)


def set_category_active(category: Category, *, is_active: bool) -> Category:
    if category.is_active == is_active:
        return category
    with transaction.atomic():
        category = Category.objects.select_for_update().get(id=category.id)
        if is_active and category.parent and not category.parent.is_active:  # K4
            raise ParentCategoryInactive()
        if not is_active and category.children.filter(is_active=True).exists():  # K5
            raise CategoryHasActiveChildren()
        # K6: produtos da categoria continuam ativos.
        category.is_active = is_active
        category.save(update_fields=["is_active", "updated_at"])
    return category
