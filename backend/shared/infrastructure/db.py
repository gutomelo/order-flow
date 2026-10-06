"""Utilitários de banco sem regra de negócio."""

from django.db import IntegrityError, OperationalError, connection


def violated_constraint(error: IntegrityError) -> str:
    """Nome da constraint violada, informado pelo PostgreSQL (psycopg `diag.constraint_name`).

    Permite traduzir cada UNIQUE/CHECK no erro de domínio certo sem depender do texto da mensagem.
    """
    diag = getattr(error.__cause__, "diag", None)
    return getattr(diag, "constraint_name", None) or ""


LOCK_NOT_AVAILABLE = "55P03"  # SQLSTATE do `lock_timeout` estourado


def set_local_lock_timeout(milliseconds: int) -> None:
    """Limita a espera por locks até o fim da transação atual (`SET LOCAL lock_timeout`).

    `set_config(..., true)` aceita parâmetro (o comando `SET` não aceita bind de valores).
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('lock_timeout', %s, true)", [f"{milliseconds}ms"])


def is_lock_timeout(error: OperationalError) -> bool:
    return getattr(error.__cause__, "sqlstate", None) == LOCK_NOT_AVAILABLE
