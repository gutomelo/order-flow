from rest_framework.routers import SimpleRouter

from apps.pricing.api.views import PriceListItemViewSet, PriceListViewSet

router = SimpleRouter(trailing_slash=False)
router.register("price-lists", PriceListViewSet, basename="price-list")
router.register(
    r"price-lists/(?P<price_list_pk>[0-9a-fA-F-]{36})/items",
    PriceListItemViewSet,
    basename="price-list-item",
)

urlpatterns = router.urls
