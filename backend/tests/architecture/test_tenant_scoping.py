"""Rede de segurança do ADR-013: toda tabela de negócio pertence a uma organização."""

import pytest
from django.apps import apps

pytestmark = pytest.mark.unit

# Exceções explícitas e justificadas. Adicionar algo aqui exige revisão de segurança.
NOT_TENANT_SCOPED = {
    "identity.Organization": "é o próprio tenant",
}


def _business_models() -> list[str]:
    return [
        model._meta.label
        for config in apps.get_app_configs()
        if config.name.startswith("apps.")
        for model in config.get_models()
    ]


@pytest.mark.parametrize("label", _business_models())
def test_every_business_model_belongs_to_an_organization(label: str) -> None:
    if label in NOT_TENANT_SCOPED:
        pytest.skip(NOT_TENANT_SCOPED[label])

    field_names = {field.name for field in apps.get_model(label)._meta.get_fields()}

    assert "organization" in field_names, f"{label} precisa de `organization` (ADR-013)"
