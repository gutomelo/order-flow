"""Eventos de identidade. Nunca carregam token ou link: o e-mail gera o link na hora do envio
(`application.passwords.password_setup_link`), então nada secreto fica no outbox ou no broker."""

from dataclasses import dataclass
from uuid import UUID

from shared.events.base import DomainEvent


@dataclass(frozen=True, kw_only=True)
class UserInvited(DomainEvent):
    event_name = "identity.user.invited"

    organization_id: UUID
    user_id: UUID


@dataclass(frozen=True, kw_only=True)
class PasswordResetRequested(DomainEvent):
    event_name = "identity.password_reset.requested"

    organization_id: UUID
    user_id: UUID
