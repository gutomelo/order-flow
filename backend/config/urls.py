from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from shared.infrastructure import health

# Rotas versionadas da API: cada módulo inclui as suas aqui.
api_v1_patterns: list[URLPattern | URLResolver] = [
    path("", include("apps.identity.api.urls")),
    path("", include("apps.suppliers.api.urls")),
    path("", include("apps.catalog.api.urls")),
]

urlpatterns = [
    path("api/v1/", include((api_v1_patterns, "api"), namespace="v1")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("health/live", health.live, name="health-live"),
    path("health/ready", health.ready, name="health-ready"),
    path("admin/", admin.site.urls),
]

# Respostas JSON no envelope padrão, inclusive fora das views DRF (ex.: rota inexistente).
handler400 = "shared.exceptions.views.bad_request"
handler403 = "shared.exceptions.views.permission_denied"
handler404 = "shared.exceptions.views.not_found"
handler500 = "shared.exceptions.views.server_error"
