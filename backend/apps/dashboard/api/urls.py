from django.urls import path

from apps.dashboard.api.views import DashboardView

urlpatterns = [path("dashboard", DashboardView.as_view(), name="dashboard")]
