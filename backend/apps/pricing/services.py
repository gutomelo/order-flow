"""Escrita de tabelas de preço (módulo simples: regras cabem em um serviço)."""

from decimal import Decimal
from uuid import UUID

import structlog
from django.db import IntegrityError, transaction

from apps.catalog.selectors import get_sellable_products
from apps.customers.models import CustomerSegment
from apps.pricing.exceptions import (
    PriceItemAlreadyExists,
    PriceListAlreadyExists,
    PriceListNameAlreadyInUse,
    ProductNotAvailable,
    SegmentNotAvailable,
)
from apps.pricing.models import PriceList, PriceListItem
from shared.domain.money import quantize
from shared.infrastructure.db import violated_constraint

logger = structlog.get_logger(__name__)


def _save_list(price_list: PriceList) -> PriceList:
    try:
        with transaction.atomic():
            price_list.save()
    except IntegrityError as exc:
        if violated_constraint(exc) == "pricing_price_list_org_name_uniq":
            raise PriceListNameAlreadyInUse(details={"field": "name"}) from exc
        raise PriceListAlreadyExists(details={"field": "segment_id"}) from exc  # PR1
    return price_list


def create_price_list(organization_id: UUID, *, name: str, segment_id: UUID | None) -> PriceList:
    segment = None
    if segment_id is not None:
        segment = (
            CustomerSegment.objects.for_organization(organization_id)
            .filter(id=segment_id, is_active=True)
            .first()
        )
        if segment is None:  # PR5
            raise SegmentNotAvailable(details={"field": "segment_id"})
    price_list = _save_list(
        PriceList(organization_id=organization_id, name=name.strip(), segment=segment)
    )
    logger.info("pricing.price_list.created", price_list_id=str(price_list.id))
    return price_list


def rename_price_list(price_list: PriceList, *, name: str) -> PriceList:
    # PR7: o segmento não muda depois de criado; só o nome.
    price_list.name = name.strip()
    return _save_list(price_list)


def delete_price_list(price_list: PriceList) -> None:
    # PR6: pedidos submetidos guardam o preço; rascunhos são recotados.
    price_list_id = str(price_list.id)
    price_list.delete()
    logger.info("pricing.price_list.deleted", price_list_id=price_list_id)


def add_item(price_list: PriceList, *, product_id: UUID, unit_price: Decimal) -> PriceListItem:
    if not get_sellable_products(price_list.organization_id, [product_id]):  # PR5
        raise ProductNotAvailable(details={"field": "product_id"})
    try:
        with transaction.atomic():
            return PriceListItem.objects.create(
                organization_id=price_list.organization_id,
                price_list=price_list,
                product_id=product_id,
                unit_price=quantize(unit_price),
            )
    except IntegrityError as exc:  # PR3
        raise PriceItemAlreadyExists(details={"field": "product_id"}) from exc


def change_item_price(item: PriceListItem, *, unit_price: Decimal) -> PriceListItem:
    item.unit_price = quantize(unit_price)
    item.save(update_fields=["unit_price", "updated_at"])
    return item


def remove_item(item: PriceListItem) -> None:
    item.delete()
