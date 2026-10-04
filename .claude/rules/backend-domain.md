---
paths:
  - "backend/apps/*/domain/**"
  - "backend/apps/*/application/**"
  - "backend/shared/domain/**"
  - "backend/shared/events/**"
---

# Domínio e Application Layer

- **Application coordena, Domain decide.** O use case busca dados, abre a transação, chama regras
  do domínio, persiste e publica eventos. O domínio responde "pode?" e "quanto?".
- Use cases nomeados por intenção, verbo no imperativo: `PlaceOrder`, `CancelOrder`,
  `ReserveStock`, `ApprovePayment`. Um arquivo por use case em `application/commands/`.
  Leituras complexas em `application/queries/`.
- Entrada de use case: dataclass imutável (`@dataclass(frozen=True)`) com tipos primitivos/UUID/Decimal.
  Não passar `request` nem serializer para a application layer.
- Transições de estado do pedido **somente** via `OrderStateMachine` (domínio). Toda transição
  grava `OrderStatusHistory` (de, para, quem, quando, motivo).
- Invariantes críticas também viram constraint no banco (CHECK/UNIQUE). Domínio = mensagem clara;
  banco = última linha de defesa.
- Domain Events: classes no passado (`OrderCreated`), imutáveis, payload apenas com primitivos
  serializáveis (UUIDs como string, Decimal como string), com `event_id`, `occurred_at`, `version`.
  Publicados via `shared.events` e despachados **após o commit**.
- Strategy/State/Specification só quando houver variação real de comportamento. Documente no
  docstring da abstração qual problema ela resolve.
- Domínio anêmico é sinal de alerta: se a regra está no serializer ou na view, mova para cá.
- Ports (ex.: `PaymentGateway`) são `typing.Protocol` pequenos, definidos no módulo que os consome.
