from enum import StrEnum


class NotificationKind(StrEnum):
    ORDER_CONFIRMED = "ORDER_CONFIRMED"
    ORDER_PAID = "ORDER_PAID"
    ORDER_SHIPPED = "ORDER_SHIPPED"
    ORDER_DELIVERED = "ORDER_DELIVERED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_REFUNDED = "ORDER_REFUNDED"
    STOCK_LOW = "STOCK_LOW"
    USER_INVITATION = "USER_INVITATION"
    PASSWORD_RESET = "PASSWORD_RESET"  # noqa: S105 (nome do tipo de aviso, não uma senha)


class NotificationStatus(StrEnum):
    PENDING = "PENDING"  # na fila de envio (ou aguardando nova tentativa)
    SENT = "SENT"
    FAILED = "FAILED"  # tentativas esgotadas
    SKIPPED = "SKIPPED"  # sem destinatário (cliente sem e-mail, conta desativada antes do envio)


# E-mails de segurança: o corpo leva um link com token, gerado na hora do envio e nunca guardado.
SECURITY_KINDS = frozenset({NotificationKind.USER_INVITATION, NotificationKind.PASSWORD_RESET})
