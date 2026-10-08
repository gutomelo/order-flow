from shared.exceptions import DomainError


class ShippingUnavailable(DomainError):
    # Nada mudou (nem pedido nem estoque): despachar de novo é seguro (etiqueta idempotente).
    code = "SHIPPING_PROVIDER_UNAVAILABLE"
    http_status = 503
    default_message = "A transportadora não respondeu. Tente despachar de novo em instantes."
