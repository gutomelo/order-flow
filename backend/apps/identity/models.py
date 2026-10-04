import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Usuário do sistema.

    Criado na Phase 1 apenas para fixar `AUTH_USER_MODEL` antes do primeiro migrate (trocar o
    modelo de usuário depois exige reescrever migrations). Equipes, roles e permissões chegam na
    Phase 2.
    """

    # UUID como identificador público: IDs sequenciais não são expostos na API.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField("email address", unique=True)

    class Meta:
        db_table = "identity_user"
        ordering = ("username",)

    def __str__(self) -> str:
        return self.username
