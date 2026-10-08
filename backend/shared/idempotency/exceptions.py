from shared.exceptions import DomainError


class IdempotencyKeyRequired(DomainError):
    code = "IDEMPOTENCY_KEY_REQUIRED"
    http_status = 400
    default_message = "Envie o header Idempotency-Key (UUID) nesta operação."


class IdempotencyKeyReused(DomainError):
    code = "IDEMPOTENCY_KEY_REUSED"
    http_status = 422
    default_message = "Esta Idempotency-Key já foi usada com outro conteúdo."


class IdempotencyRequestInProgress(DomainError):
    code = "IDEMPOTENCY_REQUEST_IN_PROGRESS"
    http_status = 409
    default_message = "Uma requisição com esta Idempotency-Key ainda está em andamento."
