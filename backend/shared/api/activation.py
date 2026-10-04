"""Ações `activate`/`deactivate` padronizadas (inativação no lugar de exclusão)."""

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response


class ActivationActionsMixin:
    """Expõe `POST {id}/activate` e `POST {id}/deactivate`.

    A view implementa `set_active(instance, is_active)` chamando o serviço do módulo — é lá que
    ficam as regras (ex.: categoria com subcategorias ativas não pode ser inativada).
    """

    def set_active(self, instance: Any, *, is_active: bool) -> Any:
        raise NotImplementedError

    def _respond_with_active(self, is_active: bool) -> Response:
        view: Any = self
        updated = self.set_active(view.get_object(), is_active=is_active)
        return Response(view.get_serializer(updated).data)

    @extend_schema(request=None)
    @action(detail=True, methods=["post"])
    def activate(self, request: Request, pk: str | None = None) -> Response:
        return self._respond_with_active(True)

    @extend_schema(request=None)
    @action(detail=True, methods=["post"])
    def deactivate(self, request: Request, pk: str | None = None) -> Response:
        return self._respond_with_active(False)
