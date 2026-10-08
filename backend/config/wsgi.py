import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

# Antes de montar a aplicação: o instrumentador do Django insere o próprio middleware (ADR-015).
from shared.observability.tracing import configure_tracing

configure_tracing(os.environ.get("SERVICE_NAME", "orderflow-api"), web=True)

application = get_wsgi_application()
