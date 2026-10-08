from celery import shared_task

from apps.audit.application.retention import purge_expired_audit_logs


@shared_task(name="maintenance.purge_expired_audit_logs", queue="maintenance")
def purge_expired() -> int:
    return purge_expired_audit_logs()
