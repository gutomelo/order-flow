"""Settings de produção: seguros por padrão, sem valores default para segredos."""

from django.core.exceptions import ImproperlyConfigured

from .base import *
from .environment import env

# HMAC-SHA256 exige chave de pelo menos 32 bytes (RFC 7518 §3.2); falha cedo, no boot.
if len(SIMPLE_JWT["SIGNING_KEY"].encode()) < 32:
    raise ImproperlyConfigured("JWT_SIGNING_KEY/DJANGO_SECRET_KEY precisa ter pelo menos 32 bytes.")

DEBUG = False
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 365)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
# Probes de health do orquestrador/load balancer costumam usar HTTP interno: sem redirect.
SECURE_REDIRECT_EXEMPT = [r"^health/"]

# Schema e Swagger não são públicos em produção (expõem o mapa da API).
SPECTACULAR_SETTINGS = {
    **SPECTACULAR_SETTINGS,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAdminUser"],
}
