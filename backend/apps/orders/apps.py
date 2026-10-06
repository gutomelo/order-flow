from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.orders"
    label = "orders"
    verbose_name = "Orders"

    def ready(self) -> None:
        # Registra os handlers de eventos (outbox) deste módulo.
        import apps.orders.handlers  # noqa: F401
