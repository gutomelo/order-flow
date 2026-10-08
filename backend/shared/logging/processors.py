"""Processadores structlog do projeto."""

from collections.abc import Mapping, MutableMapping
from typing import Any

REDACTED = "[REDACTED]"

# Fragmentos de chave que nunca podem aparecer em log com valor real (security.md).
_SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "cookie",
    "api_key",
    "apikey",
    "card",
    "cvv",
)


def _is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in _SENSITIVE_KEY_FRAGMENTS)


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: REDACTED if _is_sensitive(str(k)) else _redact(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return type(value)(_redact(item) for item in value)
    return value


def redact_sensitive_data(
    _logger: Any, _method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Rede de segurança: mascara chaves sensíveis conhecidas, inclusive em estruturas aninhadas.

    Não substitui a regra de nunca logar dados sensíveis — apenas reduz o dano de um descuido.
    """
    for key in list(event_dict.keys()):
        if key == "event":
            continue
        event_dict[key] = REDACTED if _is_sensitive(key) else _redact(event_dict[key])
    return event_dict


def add_service_name(service: str) -> Any:
    def processor(
        _logger: Any, _method_name: str, event_dict: MutableMapping[str, Any]
    ) -> MutableMapping[str, Any]:
        event_dict.setdefault("service", service)
        return event_dict

    return processor


def add_trace_ids(
    _logger: Any, _method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """`trace_id`/`span_id` do span atual (com tracing ligado): do log se chega ao trace."""
    from opentelemetry import trace

    context = trace.get_current_span().get_span_context()
    if context.is_valid:
        event_dict.setdefault("trace_id", format(context.trace_id, "032x"))
        event_dict.setdefault("span_id", format(context.span_id, "016x"))
    return event_dict
