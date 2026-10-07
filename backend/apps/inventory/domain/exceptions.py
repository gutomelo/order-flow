from shared.exceptions import DomainError


class InsufficientStock(DomainError):
    code = "INSUFFICIENT_STOCK"
    http_status = 409
    default_message = "Estoque insuficiente."


class InvalidAdjustment(DomainError):
    code = "INVALID_ADJUSTMENT"
    http_status = 422
    default_message = "A quantidade contada não pode ser menor que a quantidade reservada."


class StockChangedSinceCount(DomainError):
    code = "STOCK_CHANGED_SINCE_COUNT"
    http_status = 409
    default_message = "O saldo mudou desde a contagem. Atualize a tela e conte novamente."


class InvalidStockBalance(DomainError):
    # Defesa em profundidade: nenhum caso de uso deveria chegar aqui (as CHECKs também barram).
    code = "INVALID_STOCK_BALANCE"
    http_status = 409
    default_message = "A operação deixaria o saldo de estoque inválido."


class WarehouseInactive(DomainError):
    code = "WAREHOUSE_INACTIVE"
    http_status = 422
    default_message = "O depósito está inativo."


class WarehouseNotFound(DomainError):
    code = "WAREHOUSE_NOT_FOUND"
    http_status = 422
    default_message = "Depósito não encontrado."


class WarehouseCodeAlreadyInUse(DomainError):
    code = "WAREHOUSE_CODE_ALREADY_IN_USE"
    http_status = 409
    default_message = "Já existe um depósito com este código."


class WarehouseHasStock(DomainError):
    code = "WAREHOUSE_HAS_STOCK"
    http_status = 409
    default_message = "Zere o saldo do depósito antes de inativá-lo."


class InvalidWarehouseCode(DomainError):
    code = "INVALID_WAREHOUSE_CODE"
    http_status = 422
    default_message = "Use de 2 a 20 letras, números ou hífen."


class ReceiptAlreadyRegistered(DomainError):
    code = "RECEIPT_ALREADY_REGISTERED"
    http_status = 409
    default_message = "Este documento já foi recebido para este fornecedor."


class ProductNotAvailable(DomainError):
    code = "PRODUCT_NOT_AVAILABLE"
    http_status = 422
    default_message = "Produto não encontrado ou inativo."


class SupplierNotAvailable(DomainError):
    code = "SUPPLIER_NOT_AVAILABLE"
    http_status = 422
    default_message = "Fornecedor não encontrado ou inativo."


class SameWarehouseTransfer(DomainError):
    code = "SAME_WAREHOUSE_TRANSFER"
    http_status = 422
    default_message = "Origem e destino da transferência devem ser depósitos diferentes."


class StockItemNotFound(DomainError):
    code = "NOT_FOUND"
    http_status = 404
    default_message = "Recurso não encontrado."


class StockBusy(DomainError):
    code = "STOCK_BUSY"
    http_status = 409
    default_message = "O estoque está sendo movimentado por outra operação. Tente de novo."


class ReservationNotActive(DomainError):
    code = "RESERVATION_NOT_ACTIVE"
    http_status = 409
    default_message = "A reserva já foi encerrada."


class ReservationNotConfirmed(DomainError):
    # Envio sem reserva paga: nunca deveria acontecer (pago ⇒ CONFIRMED); barra baixa sem reserva.
    code = "RESERVATION_NOT_CONFIRMED"
    http_status = 409
    default_message = "O pedido não tem reserva de estoque confirmada para enviar."
