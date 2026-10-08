"""Papéis exclusivos dentro de um cliente (AD3, CT2).

Regra comum a endereços (cobrança, entrega padrão) e contatos (principal): se o cliente tem
registros, exatamente um tem o papel. Quem chama já travou a linha do cliente.
"""

from uuid import UUID

from django.db import models
from django.utils import timezone

from apps.customers.models import Customer


def lock_customer(customer_id: UUID) -> Customer:
    """Serializa alterações de endereços/contatos do mesmo cliente (ver customers.md, AD3)."""
    return Customer.objects.select_for_update(of=("self",)).get(id=customer_id)


def move_role(model: type[models.Model], customer_id: UUID, target_id: UUID, role: str) -> None:
    now = timezone.now()
    # Desmarca antes de marcar: o UNIQUE parcial é verificado a cada comando.
    model._default_manager.filter(customer_id=customer_id, **{role: True}).exclude(
        id=target_id
    ).update(**{role: False, "updated_at": now})
    model._default_manager.filter(id=target_id).update(**{role: True, "updated_at": now})


def promote_oldest(model: type[models.Model], customer_id: UUID, role: str) -> None:
    successor = (
        model._default_manager.filter(customer_id=customer_id).order_by("created_at", "id").first()
    )
    if successor is not None:
        move_role(model, customer_id, successor.pk, role)
