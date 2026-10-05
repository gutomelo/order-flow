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
    "purge-expired-idempotency-records": {
        "task": "maintenance.purge_expired_idempotency_records",
        "schedule": crontab(minute=17, hour=3),  # diário, fora do horário comercial
        "options": {"queue": "maintenance"},
    },
}

app.autodiscover_tasks()
