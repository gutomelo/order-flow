from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.payments"
    label = "payments"
    verbose_name = "Payments"

    def ready(self) -> None:
        # Registra os handlers de eventos (outbox) deste módulo.
        import apps.payments.application.handlers  # noqa: F401
