from shared.exceptions import DomainError


class InvalidTaxId(DomainError):
    code = "INVALID_TAX_ID"
    http_status = 422
    default_message = "CNPJ inválido."


class TaxIdAlreadyInUse(DomainError):
    code = "TAX_ID_ALREADY_IN_USE"
    http_status = 409
    default_message = "Já existe um cliente com este CNPJ."


class InvalidSegmentCode(DomainError):
    code = "INVALID_SEGMENT_CODE"
    http_status = 422
    default_message = "Código inválido: use de 2 a 30 letras, números, hífen ou sublinhado."


class SegmentCodeAlreadyInUse(DomainError):
    code = "SEGMENT_CODE_ALREADY_IN_USE"
    http_status = 409
    default_message = "Já existe um segmento com este código."


class SegmentNotAvailable(DomainError):
    code = "SEGMENT_NOT_AVAILABLE"
    http_status = 422
    default_message = "Segmento não encontrado ou inativo."


class SegmentInUse(DomainError):
    code = "SEGMENT_IN_USE"
    http_status = 409
    default_message = (
        "O segmento tem clientes ativos. Mova-os para outro segmento antes de inativá-lo."
    )


class InvalidPostalCode(DomainError):
    code = "INVALID_POSTAL_CODE"
    http_status = 422
    default_message = "CEP inválido: informe 8 dígitos."


class ContactChannelRequired(DomainError):
    code = "CONTACT_CHANNEL_REQUIRED"
    http_status = 422
    default_message = "Informe ao menos um e-mail ou telefone do contato."
