from django.urls import path

from apps.notifications.api.views import OrderNotificationsView

urlpatterns = [
    path(
        "orders/<uuid:order_id>/notifications",
        OrderNotificationsView.as_view(),
        name="order-notifications",
    ),
]
