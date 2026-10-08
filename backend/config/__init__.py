# Carrega o app Celery junto com o Django para que `shared_task` use esta instância.
from config.celery import app as celery_app

__all__ = ("celery_app",)
