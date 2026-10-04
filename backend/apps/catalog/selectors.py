"""Leituras do catálogo reutilizadas pela API e por outros módulos."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from uuid import UUID

from apps.catalog.models import MAX_CATEGORY_DEPTH, Category, Product

# Separador visual intencional entre níveis (ex.: Bebidas > Refrigerantes, com o caractere U+203A).
PATH_SEPARATOR = " \u203a "


@dataclass(frozen=True)
class CategoryNode:
    category: Category
    path: str


def category_tree(organization_id: UUID) -> list[CategoryNode]:
    """Árvore achatada em ordem de navegação (pai antes dos filhos), com caminho legível.

    A profundidade máxima de 3 níveis garante que a árvore inteira de uma organização seja
    carregada em uma única consulta e montada em memória.
    """
    categories = list(Category.objects.for_organization(organization_id).order_by("name"))
    children: dict[UUID | None, list[Category]] = {}
    for category in categories:
        children.setdefault(category.parent_id, []).append(category)

    nodes: list[CategoryNode] = []

    def visit(parent_id: UUID | None, prefix: str) -> None:
        for category in children.get(parent_id, []):
            path = f"{prefix}{PATH_SEPARATOR}{category.name}" if prefix else category.name
            nodes.append(CategoryNode(category=category, path=path))
            visit(category.id, path)

    visit(None, "")
    return nodes


def category_path(category: Category) -> str:
    """Caminho a partir dos pais já carregados (`select_related("category__parent__parent")`)."""
    names: list[str] = []
    current: Category | None = category
    # Limitado à profundidade máxima: um ciclo vindo do banco não trava a serialização.
    while current is not None and len(names) < MAX_CATEGORY_DEPTH:
        names.append(current.name)
        current = current.parent
    return PATH_SEPARATOR.join(reversed(names))


def descendant_ids(organization_id: UUID, category_id: UUID) -> set[UUID]:
    """A própria categoria e todas as subcategorias (no máximo 3 níveis → 3 consultas).

    Expande apenas IDs ainda não visitados: mesmo que um ciclo chegasse ao banco (dado legado,
    escrita manual), a função termina em vez de entrar em laço infinito.
    """
    ids = {category_id}
    frontier: Iterable[UUID] = [category_id]
    while frontier:
        children = set(
            Category.objects.for_organization(organization_id)
            .filter(parent_id__in=frontier)
            .values_list("id", flat=True)
        )
        frontier = children - ids
        ids.update(frontier)
    return ids


def get_sellable_products(organization_id: UUID, product_ids: Sequence[UUID]) -> list[Product]:
    """Interface para outros módulos (ex.: orders): produtos ativos da organização."""
    return list(
        Product.objects.for_organization(organization_id).filter(id__in=product_ids, is_active=True)
    )
