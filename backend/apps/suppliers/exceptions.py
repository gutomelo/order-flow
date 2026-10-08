from shared.exceptions import DomainError


class InvalidTaxId(DomainError):
    code = "INVALID_TAX_ID"
    http_status = 422
    default_message = "CNPJ inválido."


class TaxIdAlreadyInUse(DomainError):
    code = "TAX_ID_ALREADY_IN_USE"
    http_status = 409
    default_message = "Já existe um fornecedor com este CNPJ."
