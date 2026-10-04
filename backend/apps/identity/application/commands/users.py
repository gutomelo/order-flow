"""Use cases de administração de usuários (docs/domain/identity.md).

Cada classe é uma intenção de negócio. Mudanças que podem remover um ADMIN bloqueiam a linha da
organização antes de contar administradores: dois ADMINs rebaixando um ao outro ao mesmo tempo
não podem deixar a organização sem administrador (invariante ID5).
"""

from dataclasses import dataclass
from uuid import UUID

import structlog
from django.db import IntegrityError, transaction

from apps.identity.domain.exceptions import EmailAlreadyInUse, TeamNotFound, UserNotFound
from apps.identity.domain.permissions import Role
from apps.identity.domain.policies import (
    ensure_admin_remains,
    ensure_not_managing_self,
    is_active_admin,
)
from apps.identity.models import Organization, Team, User, normalize_email

logger = structlog.get_logger(__name__)


def _get_team(organization_id: UUID, team_id: UUID | None) -> Team | None:
    if team_id is None:
        return None
    try:
        # ID3: a equipe precisa ser da mesma organização do usuário.
        return Team.objects.for_organization(organization_id).get(id=team_id)
    except Team.DoesNotExist as exc:
        raise TeamNotFound() from exc


def _lock_user(organization_id: UUID, user_id: UUID) -> User:
    # Ordem global de locks: organização → usuário (evita deadlock entre use cases).
    Organization.objects.select_for_update().get(id=organization_id)
    try:
        return User.objects.select_for_update().get(id=user_id, organization_id=organization_id)
    except User.DoesNotExist as exc:
        raise UserNotFound() from exc


def _other_active_admins(organization_id: UUID, excluding: UUID) -> int:
    return (
        User.objects.filter(organization_id=organization_id, role=Role.ADMIN, is_active=True)
        .exclude(id=excluding)
        .count()
    )


@dataclass(frozen=True)
class CreateUserCommand:
    organization_id: UUID
    actor_id: UUID
    email: str
    password: str
    first_name: str
    last_name: str
    role: Role
    team_id: UUID | None = None


class CreateUser:
    def execute(self, command: CreateUserCommand) -> User:
        email = normalize_email(command.email)
        with transaction.atomic():
            team = _get_team(command.organization_id, command.team_id)
            if User.objects.filter(email=email).exists():
                raise EmailAlreadyInUse()
            try:
                user = User.objects.create_user(
                    email,
                    command.password,
                    organization_id=command.organization_id,
                    first_name=command.first_name,
                    last_name=command.last_name,
                    role=command.role,
                    team=team,
                )
            except IntegrityError as exc:
                # Corrida entre duas criações com o mesmo e-mail: o UNIQUE do banco decide.
                raise EmailAlreadyInUse() from exc
        logger.info(
            "identity.user.created",
            user_id=str(user.id),
            organization_id=str(command.organization_id),
            actor_id=str(command.actor_id),
            role=user.role,
        )
        return user


@dataclass(frozen=True)
class UpdateUserProfileCommand:
    organization_id: UUID
    user_id: UUID
    first_name: str | None = None
    last_name: str | None = None
    team_id: UUID | None = None
    clear_team: bool = False


class UpdateUserProfile:
    """Atualiza dados cadastrais. Papel e status têm use cases próprios (regras e registro)."""

    def execute(self, command: UpdateUserProfileCommand) -> User:
        with transaction.atomic():
            try:
                user = User.objects.select_for_update().get(
                    id=command.user_id, organization_id=command.organization_id
                )
            except User.DoesNotExist as exc:
                raise UserNotFound() from exc
            if command.first_name is not None:
                user.first_name = command.first_name
            if command.last_name is not None:
                user.last_name = command.last_name
            if command.clear_team:
                user.team = None
            elif command.team_id is not None:
                user.team = _get_team(command.organization_id, command.team_id)
            user.save(update_fields=["first_name", "last_name", "team"])
        return user


@dataclass(frozen=True)
class ChangeUserRoleCommand:
    organization_id: UUID
    actor_id: UUID
    user_id: UUID
    role: Role


class ChangeUserRole:
    def execute(self, command: ChangeUserRoleCommand) -> User:
        ensure_not_managing_self(command.actor_id, command.user_id)
        with transaction.atomic():
            user = _lock_user(command.organization_id, command.user_id)
            previous_role = Role(user.role)
            if previous_role is command.role:
                return user
            ensure_admin_remains(
                target_is_active_admin=is_active_admin(role=user.role, is_active=user.is_active),
                target_will_be_active_admin=is_active_admin(
                    role=command.role, is_active=user.is_active
                ),
                other_active_admins=_other_active_admins(command.organization_id, user.id),
            )
            user.role = command.role
            user.save(update_fields=["role"])
        # Registro de alteração de permissão; vira AuditLog USER_PERMISSION_CHANGED na Phase 12.
        logger.info(
            "identity.user.role_changed",
            user_id=str(user.id),
            organization_id=str(command.organization_id),
            actor_id=str(command.actor_id),
            from_role=previous_role.value,
            to_role=command.role.value,
        )
        return user


@dataclass(frozen=True)
class SetUserActiveCommand:
    organization_id: UUID
    actor_id: UUID
    user_id: UUID
    is_active: bool


class SetUserActive:
    """Ativa ou desativa um usuário. Desativado, ele perde o acesso na próxima requisição."""

    def execute(self, command: SetUserActiveCommand) -> User:
        ensure_not_managing_self(command.actor_id, command.user_id)
        with transaction.atomic():
            user = _lock_user(command.organization_id, command.user_id)
            if user.is_active == command.is_active:
                return user
            ensure_admin_remains(
                target_is_active_admin=is_active_admin(role=user.role, is_active=user.is_active),
                target_will_be_active_admin=is_active_admin(
                    role=user.role, is_active=command.is_active
                ),
                other_active_admins=_other_active_admins(command.organization_id, user.id),
            )
            user.is_active = command.is_active
            user.save(update_fields=["is_active"])
        logger.info(
            "identity.user.activated" if command.is_active else "identity.user.deactivated",
            user_id=str(user.id),
            organization_id=str(command.organization_id),
            actor_id=str(command.actor_id),
        )
        return user
