import pytest
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    # O throttling usa o cache: cada teste começa com contadores zerados.
    cache.clear()
