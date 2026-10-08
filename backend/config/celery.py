"""Aplicação Celery (ADR-005).

Filas separadas por natureza para que uma integração lenta não atrase notificações nem a
manutenção periódica. Políticas de retry/idempotência: `.claude/rules/async-tasks.md`.
"""

import os

from celery import Celery
from celery.schedules import crontab
from kombu import Queue

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("orderflow")
app.config_from_object("django.conf:settings", namespace="CELERY")

app.conf.task_queues = (
    Queue("default"),
    Queue("notifications"),
    Queue("integrations"),
    Queue("maintenance"),
)
app.conf.task_default_queue = "default"

# Tarefas periódicas entram aqui a partir das fases que as introduzem
# (ex.: orders.expire_unpaid_orders na Phase 7).
app.conf.beat_schedule = {
    # Outbox (ADR-011): eventos gravados com o negócio são entregues em poucos segundos.
    "relay-outbox": {"task": "events.relay_outbox", "schedule": 5.0},
    "reconcile-pending-payments": {
        "task": "maintenance.reconcile_pending_payments",
        "schedule": 60.0,
        "options": {"queue": "integrations"},
    },
    # Rastreio: remessas em trânsito com consulta vencida (o intervalo fica na própria remessa).
    "track-shipments": {
        "task": "maintenance.track_shipments",
        "schedule": 60.0,
        "options": {"queue": "integrations"},
    },
    # Avisos pendentes parados (enfileiramento perdido, worker que caiu) voltam para a fila.
    "requeue-stale-notifications": {
        "task": "maintenance.requeue_stale_notifications",
        "schedule": 300.0,
        "options": {"queue": "maintenance"},
    },
    # Retenção da auditoria: mensal, de madrugada (docs/domain/audit.md).
    "purge-expired-audit-logs": {
        "task": "maintenance.purge_expired_audit_logs",
        "schedule": crontab(minute=30, hour=3, day_of_month=1),
        "options": {"queue": "maintenance"},
    },
    "purge-published-events": {
        "task": "maintenance.purge_published_events",
        "schedule": crontab(minute=50, hour=4),
        "options": {"queue": "maintenance"},
    },
    # Reserva vencida devolve o estoque e o pedido volta a PENDING (docs/domain/orders.md).
    "expire-unpaid-orders": {
        "task": "maintenance.expire_unpaid_orders",
        "schedule": 60.0,
        "options": {"queue": "maintenance"},
    },
    "cancel-stale-pending-orders": {
        "task": "maintenance.cancel_stale_pending_orders",
        "schedule": crontab(minute=5, hour=4),
        "options": {"queue": "maintenance"},
    },
    "reconcile-stock": {
        "task": "maintenance.reconcile_stock",
        "schedule": crontab(minute=35, hour=4),
        "options": {"queue": "maintenance"},
    },
    "purge-expired-idempotency-records": {
        "task": "maintenance.purge_expired_idempotency_records",
        "schedule": crontab(minute=17, hour=3),  # diário, fora do horário comercial
        "options": {"queue": "maintenance"},
    },
}

app.autodiscover_tasks()
