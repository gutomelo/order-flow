from typing import Any, cast

import factory
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.identity.domain.permissions import Role
from apps.identity.models import Organization, Team, User

DEFAULT_PASSWORD = "Pedido-Seguro-2026!"


class OrganizationFactory(factory.django.DjangoModelFactory):  # type: ignore[type-arg]
    class Meta:
        model = Organization

    name = factory.Faker("company", locale="pt_BR")
    slug = factory.Sequence(lambda n: f"org-{n}")


class TeamFactory(factory.django.DjangoModelFactory):  # type: ignore[type-arg]
    class Meta:
        model = Team

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.Sequence(lambda n: f"Equipe {n}")


class UserFactory(factory.django.DjangoModelFactory):  # type: ignore[type-arg]
    class Meta:
        model = User
        skip_postgeneration_save = True

    organization = factory.SubFactory(OrganizationFactory)
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Faker("first_name", locale="pt_BR")
    last_name = factory.Faker("last_name", locale="pt_BR")
    role = Role.VIEWER

    @factory.post_generation  # type: ignore[untyped-decorator]
    def password(self, create: bool, extracted: str | None, **kwargs: Any) -> None:
        # Em post_generation, `self` é a instância do model criada pela factory.
        user = cast(User, self)
        user.set_password(extracted or DEFAULT_PASSWORD)
        if create:
            user.save(update_fields=["password"])


# Funções tipadas para os testes: as factories do factory_boy não informam ao mypy o tipo do
# objeto criado.
def make_organization(**kwargs: Any) -> Organization:
    return cast(Organization, OrganizationFactory(**kwargs))


def make_team(**kwargs: Any) -> Team:
    return cast(Team, TeamFactory(**kwargs))


def make_user(**kwargs: Any) -> User:
    return cast(User, UserFactory(**kwargs))


def authenticated_client(user: User) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client
