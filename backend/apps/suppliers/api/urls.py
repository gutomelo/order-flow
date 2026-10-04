from rest_framework.routers import SimpleRouter

from apps.suppliers.api.views import SupplierViewSet

router = SimpleRouter(trailing_slash=False)
router.register("suppliers", SupplierViewSet, basename="supplier")

urlpatterns = router.urls
