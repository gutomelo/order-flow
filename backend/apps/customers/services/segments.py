import re
from uuid import UUID

import structlog
from django.db import IntegrityError, transaction

from apps.customers.exceptions import InvalidSegmentCode, SegmentCodeAlreadyInUse, SegmentInUse
from apps.customers.models import SEGMENT_CODE_PATTERN, Customer, CustomerSegment

logger = structlog.get_logger(__name__)

_CODE = re.compile(SEGMENT_CODE_PATTERN)


def _normalize_code(raw: str) -> str:
    code = raw.strip().upper()
    if not _CODE.fullmatch(code):  # SG1
        raise InvalidSegmentCode(details={"field": "code"})
    return code


def create_segment(
    organization_id: UUID, *, code: str, name: str, description: str = ""
) -> CustomerSegment:
    try:
        with transaction.atomic():
            segment = CustomerSegment.objects.create(
                organization_id=organization_id,
                code=_normalize_code(code),
                name=name.strip(),
                description=description.strip(),
            )
    except IntegrityError as exc:
        raise SegmentCodeAlreadyInUse(details={"field": "code"}) from exc
    logger.info("customers.segment.created", segment_id=str(segment.id))
    return segment


def update_segment(
    segment: CustomerSegment, *, name: str | None = None, description: str | None = None
) -> CustomerSegment:
    # SG1: o código identifica o segmento em tabelas de preço e relatórios; não muda.
    if name is not None:
        segment.name = name.strip()
    if description is not None:
        segment.description = description.strip()
    segment.save(update_fields=["name", "description", "updated_at"])
    return segment


def set_segment_active(segment: CustomerSegment, *, is_active: bool) -> CustomerSegment:
    with transaction.atomic():
        # O lock serializa com quem atribui o segmento a um cliente (CU4): a contagem abaixo
        # não pode ficar desatualizada antes do commit.
        segment = CustomerSegment.objects.select_for_update().get(id=segment.id)
        if segment.is_active == is_active:
            return segment
        if not is_active:
            active_customers = Customer.objects.filter(segment=segment, is_active=True).count()
            if active_customers:  # SG2
                raise SegmentInUse(details={"active_customers": active_customers})
        segment.is_active = is_active
        segment.save(update_fields=["is_active", "updated_at"])
    logger.info(
        "customers.segment.activated" if is_active else "customers.segment.deactivated",
        segment_id=str(segment.id),
    )
    return segment
