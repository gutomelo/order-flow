from typing import Self, TypeVar
from uuid import UUID

from django.conf import settings
from django.db import models

_M = TypeVar("_M", bound=models.Model)


class TenantScopedQuerySet(models.QuerySet[_M]):
    def for_organization(self, organization_id: UUID) -> Self:
        return self.filter(organization_id=organization_id)


class TenantScopedModel(models.Model):
    """Base de toda tabela de negócio: o registro pertence a exatamente uma organização.

    Unicidades de negócio devem incluir `organization` (ex.: UNIQUE (organization_id, sku)).
    Um teste de arquitetura falha se um model de `apps/` não tiver este campo.
    """

    organization = models.ForeignKey(
        settings.TENANT_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        db_index=True,
    )

    objects = TenantScopedQuerySet.as_manager()

    class Meta:
        abstract = True
