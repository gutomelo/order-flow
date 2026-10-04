"""Serializers de identity: apenas formato e validação de entrada; regras ficam nos use cases."""

from typing import Any

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.identity.domain.permissions import Role, permissions_for
from apps.identity.models import Organization, Team, User

ROLE_CHOICES = [role.value for role in Role]


class TeamSummarySerializer(serializers.ModelSerializer[Team]):
    class Meta:
        model = Team
        fields = ("id", "name")


class OrganizationSummarySerializer(serializers.ModelSerializer[Organization]):
    class Meta:
        model = Organization
        fields = ("id", "name", "slug")


class CurrentUserSerializer(serializers.ModelSerializer[User]):
    """Usuário autenticado + permissões efetivas (o frontend usa só para UX)."""

    full_name = serializers.CharField(read_only=True)
    team = TeamSummarySerializer(read_only=True)
    organization = OrganizationSummarySerializer(read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "team",
            "organization",
            "permissions",
        )
        read_only_fields = fields

    def get_permissions(self, user: User) -> list[str]:
        return sorted(permission.value for permission in permissions_for(user.role))


class LoginSerializer(serializers.Serializer[dict[str, Any]]):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)


class LoginResponseSerializer(serializers.Serializer[dict[str, Any]]):
    access = serializers.CharField()
    user = CurrentUserSerializer()


class AccessTokenSerializer(serializers.Serializer[dict[str, Any]]):
    access = serializers.CharField()


class UserSerializer(serializers.ModelSerializer[User]):
    full_name = serializers.CharField(read_only=True)
    team = TeamSummarySerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "team",
            "is_active",
            "last_login",
            "date_joined",
        )
        read_only_fields = fields


class UserCreateSerializer(serializers.Serializer[dict[str, Any]]):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, allow_blank=True, default="")
    role = serializers.ChoiceField(choices=ROLE_CHOICES)
    team_id = serializers.UUIDField(required=False, allow_null=True, default=None)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        # Política de senha do Django (tamanho, senhas comuns, similaridade com os dados).
        candidate = User(
            email=attrs["email"], first_name=attrs["first_name"], last_name=attrs["last_name"]
        )
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs


class UserUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    team_id = serializers.UUIDField(required=False, allow_null=True)


class ChangeRoleSerializer(serializers.Serializer[dict[str, Any]]):
    role = serializers.ChoiceField(choices=ROLE_CHOICES)


class TeamSerializer(serializers.ModelSerializer[Team]):
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Team
        fields = ("id", "name", "member_count", "created_at")
        read_only_fields = fields


class TeamWriteSerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField(max_length=100)
