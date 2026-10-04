from shared.exceptions import DomainError


class SkuAlreadyInUse(DomainError):
    code = "SKU_ALREADY_IN_USE"
    http_status = 409
    default_message = "Já existe um produto com este SKU."


class BarcodeAlreadyInUse(DomainError):
    code = "BARCODE_ALREADY_IN_USE"
    http_status = 409
    default_message = "Já existe um produto com este código de barras."


class InvalidSku(DomainError):
    code = "INVALID_SKU"
    http_status = 422
    default_message = "SKU inválido: use letras, números, ponto, hífen ou sublinhado (até 64)."


class InvalidBarcode(DomainError):
    code = "INVALID_BARCODE"
    http_status = 422
    default_message = "Código de barras inválido (GTIN-8, 12, 13 ou 14)."


class CategoryNotAvailable(DomainError):
    code = "CATEGORY_NOT_AVAILABLE"
    http_status = 422
    default_message = "Categoria não encontrada ou inativa."


class SupplierNotAvailable(DomainError):
    code = "SUPPLIER_NOT_AVAILABLE"
    http_status = 422
    default_message = "Fornecedor não encontrado ou inativo."


class CategoryDepthExceeded(DomainError):
    code = "CATEGORY_DEPTH_EXCEEDED"
    http_status = 422
    default_message = "Categorias podem ter no máximo 3 níveis."


class CategoryCycle(DomainError):
    code = "CATEGORY_CYCLE"
    http_status = 422
    default_message = "Uma categoria não pode ficar dentro de si mesma ou de uma subcategoria."


class CategoryNameAlreadyInUse(DomainError):
    code = "CATEGORY_NAME_ALREADY_IN_USE"
    http_status = 409
    default_message = "Já existe uma categoria com este nome neste nível."


class CategoryHasActiveChildren(DomainError):
    code = "CATEGORY_HAS_ACTIVE_CHILDREN"
    http_status = 409
    default_message = "Inative as subcategorias antes de inativar esta categoria."


class ParentCategoryInactive(DomainError):
    code = "PARENT_CATEGORY_INACTIVE"
    http_status = 422
    default_message = "A categoria superior está inativa."
