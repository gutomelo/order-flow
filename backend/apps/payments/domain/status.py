from enum import StrEnum


class PaymentMethod(StrEnum):
    CARD = "CARD"  # cobrança no gateway com token do provedor
    MANUAL = "MANUAL"  # baixa do financeiro (boleto, PIX, transferência conciliados fora)


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class RefundStatus(StrEnum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
