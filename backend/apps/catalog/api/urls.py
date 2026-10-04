from rest_framework.routers import SimpleRouter

from apps.catalog.api.views import CategoryViewSet, ProductViewSet

router = SimpleRouter(trailing_slash=False)
router.register("products", ProductViewSet, basename="product")
router.register("categories", CategoryViewSet, basename="category")

urlpatterns = router.urls
