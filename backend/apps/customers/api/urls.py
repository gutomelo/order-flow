from rest_framework.routers import SimpleRouter

from apps.customers.api.views import (
    AddressViewSet,
    ContactViewSet,
    CustomerViewSet,
    SegmentViewSet,
)

# O UUID no prefixo evita que um ID malformado chegue à query (seria 500, não 404).
_CUSTOMER = r"customers/(?P<customer_pk>[0-9a-fA-F-]{36})"

router = SimpleRouter(trailing_slash=False)
router.register("customer-segments", SegmentViewSet, basename="customer-segment")
router.register("customers", CustomerViewSet, basename="customer")
router.register(f"{_CUSTOMER}/addresses", AddressViewSet, basename="customer-address")
router.register(f"{_CUSTOMER}/contacts", ContactViewSet, basename="customer-contact")

urlpatterns = router.urls
