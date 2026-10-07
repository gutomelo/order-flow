"""Convite e redefinição de senha (docs/domain/identity.md#senhas-por-e-mail).

Token **sem estado** do Django (`default_token_generator`): assinado com a `SECRET_KEY` sobre o
hash da senha, o último login e o e-mail do usuário. Consequências:

- nada a guardar nem a vazar no banco; o token não é persistido em lugar nenhum;
- uso único: definir a senha muda o hash e invalida o token (e os links anteriores);
- expira em `PASSWORD_RESET_TIMEOUT`.
"""

from dataclasses import dataclass
from uuid import UUID

import structlog
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.identity.authentication import user_can_authenticate
from apps.identity.domain.events import PasswordResetRequested, UserInvited
from apps.identity.domain.exceptions import (
    InvalidPasswordResetToken,
    InvitationNotPending,
    UserNotFound,
    WeakPassword,
)
from apps.identity.models import User, normalize_email
from shared.events.bus import publish

logger = structlog.get_logger(__name__)


def _organization_id(user: User) -> UUID:
    # Usuários de API sempre têm organização; só superusuários da plataforma não têm (e não usam
    # convite nem redefinição pela API).
    if user.organization_id is None:
        raise ValueError("user without organization")
    return user.organization_id


def is_invitation_pending(user: User) -> bool:
    """Convidado = criado sem senha e ainda não a definiu."""
    return not user.has_usable_password()


def request_password_reset(email: str) -> None:
    """Sempre "funciona" para quem chama: a API responde igual exista ou não a conta
    (sem enumeração de e-mails). Só contas que podem entrar recebem o e-mail."""
    user = User.objects.select_related("organization").filter(email=normalize_email(email)).first()
    if user is None or not user_can_authenticate(user):
        logger.info("identity.password_reset.ignored")  # sem o e-mail: dado pessoal
        return
    with transaction.atomic():
        publish(PasswordResetRequested(organization_id=_organization_id(user), user_id=user.id))
    logger.info("identity.password_reset.requested", user_id=str(user.id))


def invite(user: User) -> None:
    """Chamado dentro da transação de quem criou (ou reenviou) o convite."""
    publish(UserInvited(organization_id=_organization_id(user), user_id=user.id))
    logger.info("identity.user.invited", user_id=str(user.id))


def resend_invitation(organization_id: UUID, user_id: UUID) -> User:
    with transaction.atomic():
        user = User.objects.filter(organization_id=organization_id, id=user_id).first()
        if user is None:
            raise UserNotFound()
        if not user.is_active or not is_invitation_pending(user):
            raise InvitationNotPending()
        invite(user)
    return user


def _user_from_uid(uid: str) -> User | None:
    try:
        user_id = UUID(force_str(urlsafe_base64_decode(uid)))
    except (TypeError, ValueError, OverflowError):
        return None
    return User.objects.select_related("organization").filter(id=user_id).first()


def reset_password(uid: str, token: str, new_password: str) -> User:
    """Define a senha (convite aceito ou senha esquecida) e encerra as sessões abertas."""
    user = _user_from_uid(uid)
    if (
        user is None
        or not user_can_authenticate(user)
        or not default_token_generator.check_token(user, token)
    ):
        logger.info("identity.password_reset.rejected")
        raise InvalidPasswordResetToken()
    try:
        validate_password(new_password, user=user)
    except ValidationError as exc:
        reasons = list(exc.messages)
        # `field` liga o erro ao campo no formulário (padrão dos erros de domínio da API).
        raise WeakPassword(
            " ".join(reasons), details={"field": "password", "reasons": reasons}
        ) from exc
    with transaction.atomic():
        user.set_password(new_password)
        user.save(update_fields=["password"])
        # Senha nova: quem estava logado com a antiga (talvez um invasor) perde a sessão.
        for outstanding in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=outstanding)
    logger.info("identity.password_reset.completed", user_id=str(user.id))
    return user


@dataclass(frozen=True)
class PasswordSetupLink:
    email: str
    first_name: str
    url: str
    valid_hours: int
    organization_name: str


def password_setup_link(user_id: UUID) -> PasswordSetupLink | None:
    """Link para o e-mail, gerado na hora do envio. `None` se a conta não pode mais entrar."""
    user = User.objects.select_related("organization").filter(id=user_id).first()
    if user is None or user.organization is None or not user_can_authenticate(user):
        return None
    uid = urlsafe_base64_encode(force_bytes(str(user.id)))
    token = default_token_generator.make_token(user)
    # Fragmento (#), não query string: o navegador não envia fragmento ao servidor, então o token
    # não aparece em logs de acesso nem no Referer.
    url = f"{settings.FRONTEND_URL}/reset-password#uid={uid}&token={token}"
    return PasswordSetupLink(
        email=user.email,
        first_name=user.first_name,
        url=url,
        valid_hours=settings.PASSWORD_RESET_TIMEOUT // 3600,
        organization_name=user.organization.name,
    )
