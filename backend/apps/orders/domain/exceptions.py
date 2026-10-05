from shared.exceptions import DomainError


class InvalidOrderTransition(DomainError):
    code = "INVALID_ORDER_TRANSITION"
    http_status = 409
    default_message = "Esta ação não é permitida no status atual do pedido."


class OrderNotEditable(DomainError):
    code = "ORDER_NOT_EDITABLE"
    http_status = 409
    default_message = "Só rascunhos podem ser editados. Pedidos enviados têm itens e preços fixos."


class EmptyOrder(DomainError):
    code = "EMPTY_ORDER"
    http_status = 422
    default_message = "Inclua ao menos um item no pedido."


class InvalidQuantity(DomainError):
    code = "INVALID_QUANTITY"
    http_status = 422
    default_message = "A quantidade de cada item deve ser de pelo menos 1."


class DuplicateOrderLine(DomainError):
    code = "DUPLICATE_ORDER_LINE"
    http_status = 422
    default_message = "O mesmo produto aparece mais de uma vez no pedido."


class PricesChanged(DomainError):
    code = "PRICES_CHANGED"
    http_status = 409
    default_message = (
        "Os preços mudaram desde a última prévia. Confira o novo total e envie de novo."
    )


class CustomerInactive(DomainError):
    code = "CUSTOMER_INACTIVE"
    http_status = 422
    default_message = "Cliente não encontrado ou inativo."


class ProductUnavailable(DomainError):
    code = "PRODUCT_UNAVAILABLE"
    http_status = 422
    default_message = "Há produtos inativos ou inexistentes no pedido."


class AddressRequired(DomainError):
    code = "ADDRESS_REQUIRED"
    http_status = 422
    default_message = "Escolha o endereço de entrega. Cadastre um endereço no cliente, se preciso."


class AddressNotAvailable(DomainError):
    code = "ADDRESS_NOT_AVAILABLE"
    http_status = 422
    default_message = "O endereço escolhido não pertence a este cliente."


class WarehouseRequired(DomainError):
    code = "WAREHOUSE_REQUIRED"
    http_status = 422
    default_message = "Escolha o depósito que vai atender o pedido."


class WarehouseNotAvailable(DomainError):
    code = "WAREHOUSE_NOT_AVAILABLE"
    http_status = 422
    default_message = "Depósito não encontrado ou inativo."


class CancelReasonRequired(DomainError):
    code = "CANCEL_REASON_REQUIRED"
    http_status = 422
    default_message = "Informe o motivo do cancelamento."
