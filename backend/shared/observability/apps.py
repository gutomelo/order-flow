from django.apps import AppConfig


class ObservabilityConfig(AppConfig):
    name = "shared.observability"
    label = "observability"
    verbose_name = "Observability"

    def ready(self) -> None:
        from shared.infrastructure.health import dependency_gauges
        from shared.observability.metrics import register_gauges

        register_gauges(
            "orderflow_dependency_up",
            "Dependência pronta (1) ou não (0): banco, cache e broker (inclusive alarme)",
            ["dependency"],
            dependency_gauges,
        )
