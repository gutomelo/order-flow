"""URLconf usado apenas nos testes de infraestrutura compartilhada."""

from typing import Any

from django.urls import path
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from config.urls import urlpatterns as project_urlpatterns
from shared.exceptions import DomainError


class StockUnavailableForTest(DomainError):
    code = "INSUFFICIENT_STOCK"
    http_status = 409
    default_message = "Estoque insuficiente."


class QuantitySerializer(serializers.Serializer[dict[str, Any]]):
    quantity = serializers.IntegerField(min_value=1)


class DomainErrorView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:
        raise StockUnavailableForTest(details={"product_id": "p-1", "available": 0})


class ValidationErrorView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request: Request) -> Response:
        serializer = QuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class UnexpectedErrorView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:
        raise RuntimeError("database password is hunter2")


class ProtectedView(APIView):
    def get(self, request: Request) -> Response:
        return Response({"ok": True})


urlpatterns = [
    path("test/domain-error", DomainErrorView.as_view()),
    path("test/validation-error", ValidationErrorView.as_view()),
    path("test/unexpected-error", UnexpectedErrorView.as_view()),
    path("test/protected", ProtectedView.as_view()),
    *project_urlpatterns,
]

handler400 = "shared.exceptions.views.bad_request"
handler403 = "shared.exceptions.views.permission_denied"
handler404 = "shared.exceptions.views.not_found"
handler500 = "shared.exceptions.views.server_error"
