from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    label = "audit"
    verbose_name = "Audit"

    def ready(self) -> None:
        # Registra os handlers de eventos (outbox) deste módulo.
        import apps.audit.application.handlers  # noqa: F401
