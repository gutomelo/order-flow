"""Retenção (docs/domain/audit.md): registros mais velhos que `AUDIT_RETENTION_DAYS` (5 anos)
saem. A tabela é append-only por trigger; só esta transação liga a permissão de apagar."""

from datetime import timedelta

import structlog
from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from apps.audit.models import AuditLog

logger = structlog.get_logger(__name__)

BATCH = 5_000


def purge_expired_audit_logs() -> int:
    limit = timezone.now() - timedelta(days=settings.AUDIT_RETENTION_DAYS)
    removed = 0
    while True:  # lotes curtos: nada de transação longa segurando a tabela
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('audit.allow_purge', 'on', true)")
            ids = list(
                AuditLog.objects.filter(occurred_at__lt=limit).values_list("id", flat=True)[:BATCH]
            )
            if not ids:
                break
            AuditLog.objects.filter(id__in=ids).delete()
            removed += len(ids)
    if removed:
        logger.info("audit.log.purged", count=removed)
    return removed
