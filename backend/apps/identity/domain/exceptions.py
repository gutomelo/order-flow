from shared.exceptions import DomainError


class InvalidCredentials(DomainError):
    # Mesma resposta para qualquer motivo (e-mail inexistente, senha errada, usuário ou
    # organização inativos): não revela quais contas existem.
    code = "INVALID_CREDENTIALS"
    http_status = 401
    default_message = "E-mail ou senha inválidos."


class InvalidRefreshToken(DomainError):
    code = "INVALID_REFRESH_TOKEN"
    http_status = 401
    default_message = "Sua sessão expirou. Faça login novamente."


class LastAdminRequired(DomainError):
    code = "LAST_ADMIN_REQUIRED"
    http_status = 409
    default_message = "A organização precisa manter pelo menos um administrador ativo."


class SelfManagementNotAllowed(DomainError):
    code = "SELF_MANAGEMENT_NOT_ALLOWED"
    http_status = 409
    default_message = "Você não pode alterar o próprio papel nem desativar a própria conta."


class TeamNotFound(DomainError):
    code = "TEAM_NOT_FOUND"
    http_status = 422
    default_message = "Equipe não encontrada."


class EmailAlreadyInUse(DomainError):
    code = "EMAIL_ALREADY_IN_USE"
    http_status = 409
    default_message = "Já existe um usuário com este e-mail."


class TeamNameAlreadyInUse(DomainError):
    code = "TEAM_NAME_ALREADY_IN_USE"
    http_status = 409
    default_message = "Já existe uma equipe com este nome."


class UserNotFound(DomainError):
    code = "NOT_FOUND"
    http_status = 404
    default_message = "Recurso não encontrado."
