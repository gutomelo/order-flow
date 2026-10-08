"""Duas criações simultâneas do mesmo SKU: a UNIQUE do banco decide, sem 500."""

import threading

import pytest
from django.db import connection

from apps.catalog import services
from apps.catalog.exceptions import SkuAlreadyInUse
from apps.catalog.models import Product
from apps.identity.tests.factories import make_organization

pytestmark = [pytest.mark.concurrency, pytest.mark.django_db(transaction=True)]


def test_concurrent_creation_of_the_same_sku_yields_one_product() -> None:
    organization = make_organization()
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def create() -> None:
        try:
            barrier.wait()
            services.create_product(
                organization.id, services.ProductData(sku="DUP-1", name="Produto")
            )
            outcomes.append("created")
        except SkuAlreadyInUse:
            outcomes.append("conflict")
        finally:
            connection.close()

    threads = [threading.Thread(target=create) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["conflict", "created"]
    assert Product.objects.filter(organization=organization, sku="DUP-1").count() == 1
