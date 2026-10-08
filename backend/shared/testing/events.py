from shared.events.bus import deliver, relay_pending


def drain_events(max_rounds: int = 10) -> int:
    """Entrega síncrona do outbox nos testes (relay → handlers), até não sobrar evento.

    Em produção o relay roda no Beat e cada entrega é uma task; aqui tudo roda no processo do
    teste, na ordem, para verificar o efeito final.
    """
    delivered = 0
    for _ in range(max_rounds):
        relayed = relay_pending(deliver)
        if not relayed:
            return delivered
        delivered += relayed
    raise RuntimeError("outbox não esvaziou: handlers publicando em laço?")
