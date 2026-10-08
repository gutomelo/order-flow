from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    label = "notifications"
    verbose_name = "Notifications"

    def ready(self) -> None:
        # Registra os handlers de eventos (outbox) deste módulo.
        import apps.notifications.application.handlers  # noqa: F401
        from apps.notifications.application.metrics import register

        register()
