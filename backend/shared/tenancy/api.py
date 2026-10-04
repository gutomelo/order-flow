from typing import Any
from uuid import UUID

from django.db.models import QuerySet
from rest_framework.exceptions import NotAuthenticated
from rest_framework.generics import GenericAPIView


class TenantScopedQuerysetMixin(GenericAPIView[Any]):
    """Restringe o queryset da view à organização do usuário autenticado (ADR-013).

    O tenant vem sempre do usuário — nunca de header, URL ou corpo da requisição. Objetos de
    outra organização ficam fora do queryset e, portanto, respondem 404.
    """

    @property
    def organization_id(self) -> UUID:
        organization_id: UUID | None = getattr(self.request.user, "organization_id", None)
        if organization_id is None:
            # Usuário sem organização (ex.: superusuário da plataforma) não usa a API de negócio.
            raise NotAuthenticated()
        return organization_id

    def get_queryset(self) -> QuerySet[Any]:
        return super().get_queryset().filter(organization_id=self.organization_id)
