from dataclasses import dataclass
from uuid import UUID

from django.db import IntegrityError, transaction

from apps.identity.domain.exceptions import TeamNameAlreadyInUse, TeamNotFound
from apps.identity.models import Team


@dataclass(frozen=True)
class CreateTeamCommand:
    organization_id: UUID
    name: str


class CreateTeam:
    def execute(self, command: CreateTeamCommand) -> Team:
        try:
            with transaction.atomic():
                return Team.objects.create(
                    organization_id=command.organization_id, name=command.name.strip()
                )
        except IntegrityError as exc:
            # UNIQUE (organization_id, lower(name)) — ID4.
            raise TeamNameAlreadyInUse() from exc


@dataclass(frozen=True)
class RenameTeamCommand:
    organization_id: UUID
    team_id: UUID
    name: str


class RenameTeam:
    def execute(self, command: RenameTeamCommand) -> Team:
        try:
            with transaction.atomic():
                team = (
                    Team.objects.for_organization(command.organization_id)
                    .select_for_update()
                    .get(id=command.team_id)
                )
                team.name = command.name.strip()
                team.save(update_fields=["name", "updated_at"])
                return team
        except Team.DoesNotExist as exc:
            raise TeamNotFound() from exc
        except IntegrityError as exc:
            raise TeamNameAlreadyInUse() from exc
