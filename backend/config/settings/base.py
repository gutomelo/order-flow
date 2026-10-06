"""Settings compartilhados por todos os ambientes.

Todo valor sensível ou dependente de ambiente vem de variáveis de ambiente
(documentadas em `.env.example` na raiz do repositório).
"""

from datetime import timedelta

import django_stubs_ext
from corsheaders.defaults import default_headers

from shared.logging import build_logging_config, configure_structlog

from .environment import BASE_DIR, env

# Permite generics em classes do Django em runtime (ex.: admin.ModelAdmin[Model]), usados pelo mypy.
django_stubs_ext.monkeypatch()

# ---------------------------------------------------------------------------
# Núcleo
# ---------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS: list[str] = env.list("DJANGO_ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terceiros
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    # Infraestrutura transversal com tabela própria
    "shared.idempotency",
    # Módulos de negócio
    "apps.identity",
    "apps.customers",
    "apps.suppliers",
    "apps.catalog",
    "apps.inventory",
    "apps.pricing",
    "apps.orders",
]

MIDDLEWARE = [
    "shared.logging.middleware.RequestIdMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Modelo de usuário customizado desde o primeiro migrate: trocá-lo depois exige reescrever
# migrations de auth/admin.
AUTH_USER_MODEL = "identity.User"

# Tenant (ADR-013). Mesmo padrão de AUTH_USER_MODEL: `shared.tenancy` referencia o model pelo
# label, sem importar `apps/`.
TENANT_MODEL = "identity.Organization"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Banco de dados (ADR-004)
# ---------------------------------------------------------------------------
DATABASES = {"default": env.db("DATABASE_URL")}
# Transações explícitas nos use cases; nada de transação implícita por request.
DATABASES["default"]["ATOMIC_REQUESTS"] = False
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

# ---------------------------------------------------------------------------
# Cache (ADR-006)
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
        "TIMEOUT": 300,
    }
}

# ---------------------------------------------------------------------------
# Internacionalização e tempo
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    # JWT (ADR-007) + verificação de organização ativa a cada requisição (ADR-013).
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.identity.api.authentication.OrganizationAwareJWTAuthentication",
    ],
    # Seguro por padrão: endpoints precisam declarar explicitamente se são públicos.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_PAGINATION_CLASS": "shared.pagination.DefaultPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "shared.exceptions.handler.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("API_THROTTLE_ANON", default="60/min"),
        "user": env("API_THROTTLE_USER", default="600/min"),
        # Login e refresh: limita tentativas de força bruta (por IP).
        "auth": env("API_THROTTLE_AUTH", default="10/min"),
    },
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "OrderFlow API",
    "DESCRIPTION": "API B2B de gestão de pedidos e estoque.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]+",
    # O mesmo conjunto de status aparece em vários campos (status, from_status, to_status).
    "ENUM_NAME_OVERRIDES": {"OrderStatusEnum": "apps.orders.domain.status.OrderStatus"},
}

# ---------------------------------------------------------------------------
# Autenticação JWT (ADR-007, docs/domain/identity.md)
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_TOKEN_MINUTES", default=10)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_TOKEN_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "SIGNING_KEY": env("JWT_SIGNING_KEY", default=SECRET_KEY),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    # Usuário inativo OU organização inativa não autentica nem renova sessão (ID7).
    "USER_AUTHENTICATION_RULE": "apps.identity.authentication.user_can_authenticate",
    # Troca de senha invalida access tokens emitidos antes dela.
    "CHECK_REVOKE_TOKEN": True,
}

# Refresh token em cookie HttpOnly, inacessível a JavaScript (ADR-007).
AUTH_REFRESH_COOKIE = {
    "name": "orderflow_refresh",
    "path": "/api/v1/auth/",
    "samesite": "Strict",
    "secure": env.bool("AUTH_REFRESH_COOKIE_SECURE", default=True),
}

# ---------------------------------------------------------------------------
# CORS (somente as origens do frontend)
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS: list[str] = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_HEADERS = (*default_headers, "idempotency-key")
CORS_EXPOSE_HEADERS = ["X-Request-ID", "Idempotent-Replayed"]

# ---------------------------------------------------------------------------
# Regras de negócio configuráveis (docs/domain/inventory.md, orders.md)
# ---------------------------------------------------------------------------
# Quanto tempo a reserva segura o estoque aguardando pagamento (B2B: boleto/PIX).
STOCK_RESERVATION_TTL_HOURS = env.int("STOCK_RESERVATION_TTL_HOURS", default=48)
# Espera máxima por lock de estoque antes de responder STOCK_BUSY (ADR-008).
STOCK_LOCK_TIMEOUT_MS = env.int("STOCK_LOCK_TIMEOUT_MS", default=3000)
# Pedido PENDING sem atividade por mais que isto é cancelado (PENDING_TIMEOUT).
ORDER_PENDING_MAX_AGE_DAYS = env.int("ORDER_PENDING_MAX_AGE_DAYS", default=7)

# ---------------------------------------------------------------------------
# Celery (ADR-005)
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_TIMEOUT = 3
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
# Mantém a configuração de logging do Django (structlog) também nos workers.
CELERY_WORKER_HIJACK_ROOT_LOGGER = False

# ---------------------------------------------------------------------------
# Logging estruturado (docs/architecture/observability.md)
# ---------------------------------------------------------------------------
LOG_LEVEL = env("LOG_LEVEL", default="INFO")
LOG_FORMAT = env("LOG_FORMAT", default="json")
SERVICE_NAME = env("SERVICE_NAME", default="orderflow-api")

LOGGING = build_logging_config(
    level=LOG_LEVEL, json_output=LOG_FORMAT == "json", service=SERVICE_NAME
)
configure_structlog(service=SERVICE_NAME, json_output=LOG_FORMAT == "json")

# ---------------------------------------------------------------------------
# Segurança comum a todos os ambientes
# ---------------------------------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
