"""Evento → registro de auditoria (docs/domain/audit.md). Regra pura, sem banco: testável em
unidade. O rótulo legível da entidade (ex.: "#000003") é resolvido depois, na application."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID


class AuditAction(StrEnum):
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_STATUS_CHANGED = "ORDER_STATUS_CHANGED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    PAYMENT_STARTED = "PAYMENT_STARTED"
    PAYMENT_APPROVED = "PAYMENT_APPROVED"
    PAYMENT_RECORDED = "PAYMENT_RECORDED"  # baixa manual
    PAYMENT_DECLINED = "PAYMENT_DECLINED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_REFUNDED = "PAYMENT_REFUNDED"
    REFUND_REQUESTED = "REFUND_REQUESTED"
    REFUND_RETRIED = "REFUND_RETRIED"
    REFUND_COMPLETED = "REFUND_COMPLETED"
    REFUND_FAILED = "REFUND_FAILED"
    STOCK_RECEIVED = "STOCK_RECEIVED"
    STOCK_ADJUSTED = "STOCK_ADJUSTED"
    STOCK_TRANSFERRED = "STOCK_TRANSFERRED"
    REORDER_POINT_CHANGED = "REORDER_POINT_CHANGED"


class EntityType(StrEnum):
    ORDER = "ORDER"
    PAYMENT = "PAYMENT"
    REFUND = "REFUND"
    STOCK_ITEM = "STOCK_ITEM"


A = AuditAction


@dataclass(frozen=True)
class AuditEntry:
    action: AuditAction
    entity_type: EntityType
    entity_id: UUID
    actor_id: UUID | None
    reason: str = ""
    # Campo → [antes, depois]. Só o que mudou e não é sensível (nada de token, senha, cartão).
    changes: dict[str, Any] = field(default_factory=dict)
    order_id: UUID | None = None  # para "tudo sobre o pedido X" (pagamentos e estornos inclusos)


def _uuid(value: str | None) -> UUID | None:
    return UUID(value) if value else None


def from_order_status(payload: dict[str, Any]) -> AuditEntry:
    source, target = payload["from_status"], payload["to_status"]
    if source is None:
        action = A.ORDER_CREATED
    elif target == "CANCELLED":
        action = A.ORDER_CANCELLED
    else:
        action = A.ORDER_STATUS_CHANGED
    order_id = UUID(payload["order_id"])
    return AuditEntry(
        action=action,
        entity_type=EntityType.ORDER,
        entity_id=order_id,
        actor_id=_uuid(payload["actor_id"]),
        reason=payload["reason"],
        changes={"status": [source, target]},
        order_id=order_id,
    )


_PAYMENT_ACTIONS = {
    (None, "PENDING"): A.PAYMENT_STARTED,
    (None, "APPROVED"): A.PAYMENT_RECORDED,
    ("PENDING", "APPROVED"): A.PAYMENT_APPROVED,
    ("PENDING", "DECLINED"): A.PAYMENT_DECLINED,
    ("PENDING", "FAILED"): A.PAYMENT_FAILED,
    ("APPROVED", "REFUNDED"): A.PAYMENT_REFUNDED,
}


def from_payment_status(payload: dict[str, Any]) -> AuditEntry:
    source, target = payload["from_status"], payload["to_status"]
    return AuditEntry(
        action=_PAYMENT_ACTIONS[(source, target)],
        entity_type=EntityType.PAYMENT,
        entity_id=UUID(payload["payment_id"]),
        actor_id=_uuid(payload["actor_id"]),
        reason=payload["note"],
        changes={
            "status": [source, target],
            "amount": payload["amount"],
            "method": payload["method"],
        },
        order_id=UUID(payload["order_id"]),
    )


_REFUND_ACTIONS = {
    (None, "PENDING"): A.REFUND_REQUESTED,
    ("FAILED", "PENDING"): A.REFUND_RETRIED,
    ("PENDING", "SUCCEEDED"): A.REFUND_COMPLETED,
    ("PENDING", "FAILED"): A.REFUND_FAILED,
}


def from_refund_status(payload: dict[str, Any]) -> AuditEntry:
    source, target = payload["from_status"], payload["to_status"]
    return AuditEntry(
        action=_REFUND_ACTIONS[(source, target)],
        entity_type=EntityType.REFUND,
        entity_id=UUID(payload["refund_id"]),
        actor_id=_uuid(payload["actor_id"]),
        reason=payload["note"],
        changes={"status": [source, target], "amount": payload["amount"]},
        order_id=UUID(payload["order_id"]),
    )


_STOCK_ACTIONS = {
    "PURCHASE": A.STOCK_RECEIVED,
    "ADJUSTMENT": A.STOCK_ADJUSTED,
    "TRANSFER": A.STOCK_TRANSFERRED,
}


def from_stock_change(payload: dict[str, Any]) -> AuditEntry:
    changes: dict[str, Any] = {"on_hand": [payload["on_hand_before"], payload["on_hand_after"]]}
    if payload["reserved_before"] != payload["reserved_after"]:
        changes["reserved"] = [payload["reserved_before"], payload["reserved_after"]]
    return AuditEntry(
        action=_STOCK_ACTIONS[payload["movement_type"]],
        entity_type=EntityType.STOCK_ITEM,
        entity_id=UUID(payload["stock_item_id"]),
        actor_id=_uuid(payload["actor_id"]),
        reason=payload["reason"],
        changes=changes,
    )


def from_reorder_point(payload: dict[str, Any]) -> AuditEntry:
    return AuditEntry(
        action=A.REORDER_POINT_CHANGED,
        entity_type=EntityType.STOCK_ITEM,
        entity_id=UUID(payload["stock_item_id"]),
        actor_id=_uuid(payload["actor_id"]),
        changes={"reorder_point": [payload["before"], payload["after"]]},
    )
