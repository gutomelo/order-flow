from typing import Any, cast
from uuid import UUID

from django.db.models import Count, QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.identity.api.serializers import (
    ChangeRoleSerializer,
    TeamSerializer,
    TeamWriteSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from apps.identity.application import passwords
from apps.identity.application.commands.teams import (
    CreateTeam,
    CreateTeamCommand,
    RenameTeam,
    RenameTeamCommand,
)
from apps.identity.application.commands.users import (
    ChangeUserRole,
    ChangeUserRoleCommand,
    CreateUser,
    CreateUserCommand,
    SetUserActive,
    SetUserActiveCommand,
    UpdateUserProfile,
    UpdateUserProfileCommand,
)
from apps.identity.domain.permissions import Permission, Role
from apps.identity.models import Team, User
from shared.permissions import HasPermission
from shared.tenancy.api import TenantScopedQuerysetMixin


class UserViewSet(
    TenantScopedQuerysetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet[User],
):
    """Usuários da organização. Papel e status mudam por ações explícitas, não por PATCH."""

    queryset = User.objects.select_related("team")
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated, HasPermission(Permission.USERS_MANAGE))
    http_method_names = ("get", "post", "patch", "head", "options")
    filterset_fields = ("role", "is_active", "team")
    search_fields = ("email", "first_name", "last_name")
    ordering_fields = ("email", "first_name", "last_name", "role", "date_joined")
    ordering = ("first_name", "email")

    def _actor_id(self) -> UUID:
        return cast(User, self.request.user).id

    @extend_schema(request=UserCreateSerializer, responses={201: UserSerializer})
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = CreateUser().execute(
            CreateUserCommand(
                organization_id=self.organization_id,
                actor_id=self._actor_id(),
                email=data["email"],
                password=data["password"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                role=Role(data["role"]),
                team_id=data["team_id"],
            )
        )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=None, responses=UserSerializer)
    @action(detail=True, methods=["post"], url_path="resend-invitation")
    def resend_invitation(self, request: Request, pk: str | None = None) -> Response:
        user = self.get_object()
        user = passwords.resend_invitation(self.organization_id, user.id)
        return Response(UserSerializer(user).data)

    @extend_schema(request=UserUpdateSerializer, responses=UserSerializer)
    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        target = self.get_object()  # 404 fora da organização
        serializer = UserUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = UpdateUserProfile().execute(
            UpdateUserProfileCommand(
                organization_id=self.organization_id,
                user_id=target.pk,
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                team_id=data.get("team_id"),
                clear_team="team_id" in data and data["team_id"] is None,
            )
        )
        return Response(UserSerializer(user).data)

    @extend_schema(request=ChangeRoleSerializer, responses=UserSerializer)
    @action(detail=True, methods=["post"], url_path="change-role")
    def change_role(self, request: Request, pk: str | None = None) -> Response:
        target = self.get_object()
        serializer = ChangeRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = ChangeUserRole().execute(
            ChangeUserRoleCommand(
                organization_id=self.organization_id,
                actor_id=self._actor_id(),
                user_id=target.pk,
                role=Role(serializer.validated_data["role"]),
            )
        )
        return Response(UserSerializer(user).data)

    @extend_schema(request=None, responses=UserSerializer)
    @action(detail=True, methods=["post"])
    def deactivate(self, request: Request, pk: str | None = None) -> Response:
        return self._set_active(is_active=False)

    @extend_schema(request=None, responses=UserSerializer)
    @action(detail=True, methods=["post"])
    def activate(self, request: Request, pk: str | None = None) -> Response:
        return self._set_active(is_active=True)

    def _set_active(self, *, is_active: bool) -> Response:
        target = self.get_object()
        user = SetUserActive().execute(
            SetUserActiveCommand(
                organization_id=self.organization_id,
                actor_id=self._actor_id(),
                user_id=target.pk,
                is_active=is_active,
            )
        )
        return Response(UserSerializer(user).data)


class TeamViewSet(
    TenantScopedQuerysetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet[Team],
):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = (IsAuthenticated, HasPermission(Permission.USERS_MANAGE))
    http_method_names = ("get", "post", "patch", "head", "options")
    search_fields = ("name",)
    ordering_fields = ("name", "created_at")
    ordering = ("name",)

    def get_queryset(self) -> QuerySet[Team]:
        return cast(
            "QuerySet[Team]", super().get_queryset().annotate(member_count=Count("members"))
        )

    @extend_schema(request=TeamWriteSerializer, responses={201: TeamSerializer})
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = TeamWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team = CreateTeam().execute(
            CreateTeamCommand(
                organization_id=self.organization_id, name=serializer.validated_data["name"]
            )
        )
        return Response(
            TeamSerializer(self.get_queryset().get(pk=team.pk)).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=TeamWriteSerializer, responses=TeamSerializer)
    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        target = self.get_object()
        serializer = TeamWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        RenameTeam().execute(
            RenameTeamCommand(
                organization_id=self.organization_id,
                team_id=target.pk,
                name=serializer.validated_data["name"],
            )
        )
        return Response(TeamSerializer(self.get_queryset().get(pk=target.pk)).data)
