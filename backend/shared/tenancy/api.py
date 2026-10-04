from typing import Any
from uuid import UUID

from django.db.models import QuerySet
from rest_framework.exceptions import NotAuthenticated
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request


def organization_id_of(request: Request) -> UUID:
    """Organização do usuário autenticado — a única fonte do tenant (ADR-013)."""
    organization_id: UUID | None = getattr(request.user, "organization_id", None)
    if organization_id is None:
        # Usuário sem organização (ex.: superusuário da plataforma) não usa a API de negócio.
        raise NotAuthenticated()
    return organization_id


class TenantScopedQuerysetMixin(GenericAPIView[Any]):
    """Restringe o queryset da view à organização do usuário autenticado (ADR-013).

    O tenant vem sempre do usuário — nunca de header, URL ou corpo da requisição. Objetos de
    outra organização ficam fora do queryset e, portanto, respondem 404.
    """

    @property
    def organization_id(self) -> UUID:
        return organization_id_of(self.request)

    def get_queryset(self) -> QuerySet[Any]:
        return super().get_queryset().filter(organization_id=self.organization_id)
