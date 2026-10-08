from django.apps import AppConfig


class IdentityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.identity"
    label = "identity"
    verbose_name = "Identity"

    def ready(self) -> None:
        # Registra as extensões do OpenAPI (basta importar o módulo uma vez).
        import apps.identity.api.schema  # noqa: F401
