"""Extensões do drf-spectacular para o OpenAPI (carregadas em `IdentityConfig.ready`)."""

from typing import Any

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.plumbing import build_bearer_security_scheme_object


# A base registra a subclasse em `__init_subclass__`, sem tipos nos stubs da biblioteca.
class OrganizationAwareJWTScheme(OpenApiAuthenticationExtension):  # type: ignore[no-untyped-call]
    """Declara o Bearer JWT no schema: a subclasse do autenticador do SimpleJWT não é
    reconhecida automaticamente, e sem isto o Swagger não oferece "Authorize"."""

    target_class = "apps.identity.api.authentication.OrganizationAwareJWTAuthentication"
    name = "jwtAuth"

    def get_security_definition(self, auto_schema: Any) -> dict[str, Any]:
        return build_bearer_security_scheme_object(
            header_name="AUTHORIZATION",
            token_prefix="Bearer",  # noqa: S106 (prefixo do header, não é segredo)
            bearer_format="JWT",
        )
