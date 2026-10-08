from shared.exceptions import DomainError


class PriceNotFound(DomainError):
    code = "PRICE_NOT_FOUND"
    http_status = 422
    default_message = "Há produtos sem preço para este cliente."


class PriceListNameAlreadyInUse(DomainError):
    code = "PRICE_LIST_NAME_ALREADY_IN_USE"
    http_status = 409
    default_message = "Já existe uma tabela de preços com este nome."


class PriceListAlreadyExists(DomainError):
    code = "PRICE_LIST_ALREADY_EXISTS"
    http_status = 409
    default_message = "Já existe uma tabela de preços para este segmento (ou a tabela padrão)."


class SegmentNotAvailable(DomainError):
    code = "SEGMENT_NOT_AVAILABLE"
    http_status = 422
    default_message = "Segmento não encontrado ou inativo."


class ProductNotAvailable(DomainError):
    code = "PRODUCT_NOT_AVAILABLE"
    http_status = 422
    default_message = "Produto não encontrado ou inativo."


class PriceItemAlreadyExists(DomainError):
    code = "PRICE_ITEM_ALREADY_EXISTS"
    http_status = 409
    default_message = "Este produto já está na tabela."
