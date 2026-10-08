from shared.exceptions import DomainError


class PaymentDeclined(DomainError):
    code = "PAYMENT_DECLINED"
    http_status = 422
    default_message = "O pagamento foi recusado. Confira o cartão ou use outra forma de pagamento."


class PaymentInProgress(DomainError):
    code = "PAYMENT_IN_PROGRESS"
    http_status = 409
    default_message = "Já há uma cobrança em andamento para este pedido. Aguarde a confirmação."


class RefundNotRetryable(DomainError):
    code = "REFUND_NOT_RETRYABLE"
    http_status = 409
    default_message = "Só estornos de cartão que falharam podem ser tentados de novo."


class RefundNotManual(DomainError):
    code = "REFUND_NOT_MANUAL"
    http_status = 409
    default_message = "Só estornos de pagamentos manuais pendentes são confirmados à mão."


class InvalidPaymentTransition(DomainError):
    code = "INVALID_PAYMENT_TRANSITION"
    http_status = 409
    default_message = "Esta operação não é permitida no status atual do pagamento."
