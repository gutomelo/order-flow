"""Settings para desenvolvimento local."""

from .base import *
from .environment import env

DEBUG = env.bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = env.list(
    # "backend" é o host usado pelo proxy do Vite dentro do Docker Compose.
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "backend"],
)

# API navegável facilita a exploração manual em desenvolvimento.
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
