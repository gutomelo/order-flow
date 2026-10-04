import pytest
from django.core.management import CommandError, call_command

from apps.identity.domain.permissions import Role
from apps.identity.models import Organization, User

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def test_creates_organization_with_its_first_admin() -> None:
    call_command(
        "create_organization",
        name="Acme Distribuidora",
        admin_email="Admin@Acme.com",
        admin_password="Pedido-Seguro-2026!",
    )

    organization = Organization.objects.get(slug="acme-distribuidora")
    admin = User.objects.get(email="admin@acme.com")
    assert admin.organization == organization
    assert admin.role == Role.ADMIN


def test_rejects_weak_admin_password() -> None:
    with pytest.raises(CommandError):
        call_command("create_organization", name="X", admin_email="a@x.com", admin_password="123")

    assert not Organization.objects.exists()
