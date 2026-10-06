from django.apps import AppConfig


class EventsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "shared.events"
    label = "events"
    verbose_name = "Domain events (outbox)"
