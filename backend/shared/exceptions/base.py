from collections.abc import Mapping
from typing import Any, ClassVar


class DomainError(Exception):
    """Violação de regra de negócio.

    Subclasses definem um `code` estável (contrato com o frontend), o status HTTP e uma mensagem
    padrão em pt-BR. O exception handler da API converte a exceção para o envelope de erro.
    """

    code: ClassVar[str] = "DOMAIN_ERROR"
    http_status: ClassVar[int] = 422
    default_message: ClassVar[str] = "A operação viola uma regra de negócio."

    def __init__(self, message: str | None = None, *, details: Mapping[str, Any] | None = None):
        self.message = message or self.default_message
        self.details: dict[str, Any] = dict(details or {})
        super().__init__(self.message)
