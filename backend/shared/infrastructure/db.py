"""Utilitários de banco sem regra de negócio."""

from django.db import IntegrityError


def violated_constraint(error: IntegrityError) -> str:
    """Nome da constraint violada, informado pelo PostgreSQL (psycopg `diag.constraint_name`).

    Permite traduzir cada UNIQUE/CHECK no erro de domínio certo sem depender do texto da mensagem.
    """
    diag = getattr(error.__cause__, "diag", None)
    return getattr(diag, "constraint_name", None) or ""
