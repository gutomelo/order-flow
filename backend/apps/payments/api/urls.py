from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.payments.api.views import PaymentViewSet, RefundConfirmView, RefundRetryView

router = SimpleRouter(trailing_slash=False)
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = [
    path("refunds/<uuid:refund_id>/retry", RefundRetryView.as_view(), name="refund-retry"),
    path("refunds/<uuid:refund_id>/confirm", RefundConfirmView.as_view(), name="refund-confirm"),
    *router.urls,
]
