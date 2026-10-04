from typing import Any, cast

import pytest
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from shared.pagination import DefaultPagination

pytestmark = pytest.mark.unit


def _paginate(query: str) -> tuple[list[int] | None, DefaultPagination]:
    paginator = DefaultPagination()
    request = Request(APIRequestFactory().get(f"/items{query}"))
    return paginator.paginate_queryset(cast(Any, list(range(250))), request), paginator


def test_uses_default_page_size() -> None:
    page, _ = _paginate("")

    assert page == list(range(25))


def test_caps_page_size_requested_by_client() -> None:
    page, _ = _paginate("?page_size=1000")

    assert page is not None
    assert len(page) == 100


def test_response_contains_count_and_links() -> None:
    page, paginator = _paginate("?page=2")

    body = paginator.get_paginated_response(page).data

    assert body["count"] == 250
    assert body["previous"] is not None
    assert body["next"] is not None
    assert body["results"] == list(range(25, 50))
