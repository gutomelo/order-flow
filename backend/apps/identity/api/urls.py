from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.identity.api.auth_views import CurrentUserView, LoginView, LogoutView, RefreshView
from apps.identity.api.views import TeamViewSet, UserViewSet

router = SimpleRouter(trailing_slash=False)
router.register("users", UserViewSet, basename="user")
router.register("teams", TeamViewSet, basename="team")

urlpatterns = [
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/refresh", RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("auth/me", CurrentUserView.as_view(), name="auth-me"),
    *router.urls,
]
