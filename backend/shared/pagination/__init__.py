from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """Paginação padrão de todas as coleções: `?page=` e `?page_size=` (máximo 100)."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100
