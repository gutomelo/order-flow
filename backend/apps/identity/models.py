import uuid
from typing import Any, ClassVar

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower

from apps.identity.domain.permissions import Role, role_has_permission
from shared.tenancy.models import TenantScopedModel


def normalize_email(email: str) -> str:
    """E-mail é comparado sem diferenciar maiúsculas (invariante ID2)."""
    return email.strip().lower()


class Organization(models.Model):
    """Tenant: empresa cliente do OrderFlow (ADR-013)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=60, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "identity_organization"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Team(TenantScopedModel):
    """Agrupamento organizacional de usuários. Não restringe visibilidade de dados."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "identity_team"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                F("organization"), Lower("name"), name="identity_team_org_name_uniq"
            ),
        ]

    def __str__(self) -> str:
        return self.name


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra: Any) -> "User":
        user = self.model(email=normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra: Any) -> "User":
        # Superusuário da plataforma: opera o Django admin, não pertence a uma organização.
        extra.update(is_staff=True, is_superuser=True)
        return self.create_user(email, password, **extra)


class User(AbstractUser):
    """Usuário de uma organização (docs/domain/identity.md)."""

    # Login por e-mail: o campo `username` herdado do Django não é usado.
    username = None  # type: ignore[assignment]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField("email address", unique=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
    )
    role = models.CharField(
        max_length=20, choices=[(role.value, role.value) for role in Role], default=Role.VIEWER
    )
    team = models.ForeignKey(
        Team, on_delete=models.PROTECT, null=True, blank=True, related_name="members"
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    objects = UserManager()  # type: ignore[assignment,misc]

    class Meta:
        db_table = "identity_user"
        ordering = ("email",)
        constraints = [
            # ID1: só superusuários da plataforma existem fora de uma organização.
            models.CheckConstraint(
                condition=Q(organization__isnull=False) | Q(is_superuser=True),
                name="identity_user_org_required_check",
            ),
            # ID2: unicidade sem diferenciar maiúsculas, mesmo que algo grave sem normalizar.
            models.UniqueConstraint(Lower("email"), name="identity_user_email_ci_uniq"),
        ]
        indexes = [models.Index(fields=["organization", "role"], name="identity_user_org_role_idx")]

    def __str__(self) -> str:
        return self.email

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def has_api_permission(self, permission: str) -> bool:
        """Implementa `shared.permissions.PermissionSubject` a partir do papel do usuário."""
        if not self.is_active or self.organization_id is None:
            return False
        return role_has_permission(self.role, permission)
