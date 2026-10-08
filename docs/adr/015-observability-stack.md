# ADR-015: Observabilidade com Prometheus, OpenTelemetry e correlação ponta a ponta

- **Status:** Accepted
- **Data:** 2026-10-08
- **Decisores:** time OrderFlow (Phase 13)
- **Relacionados:** ADR-005 (Celery/RabbitMQ), ADR-011 (outbox), `docs/architecture/observability.md`

## Context

Até a Phase 12 havia logs estruturados com `request_id`, health checks e auditoria. Faltava
responder, sem debugger: *está lento? onde? está falhando quanto? o que essa requisição causou no
worker?* Dois episódios reais mostraram o buraco:

- Phase 10: com o disco cheio, o RabbitMQ bloqueou publicações e nada andava — mas a prontidão
  dizia "ok" (conectar ao broker não detecta alarme).
- O fluxo de negócio atravessa processos (API → outbox → worker → e-mail/estorno/auditoria); os
  logs do worker não diziam de que requisição vinham.

## Decision

1. **Correlação ponta a ponta.** `correlation_id` nasce com a requisição; todo `DomainEvent` o
   carrega (com `request_id` e o `traceparent` W3C); a entrega do evento (`shared.events.bus`)
   religa o contexto; tasks Celery levam o id no header `orderflow_correlation_id` (não
   `correlation_id`, propriedade AMQP que o Celery preenche com o id da task).
2. **Métricas Prometheus (pull).** `django-prometheus` para HTTP e banco; contadores de negócio
   contados **após o commit**; indicadores que já estão no banco (fila do outbox, e-mails, cobranças
   sem resposta, dependências) **lidos na coleta**. Worker com endpoint próprio (`:9100`) e modo
   multiprocesso; gunicorn de produção também (`PROMETHEUS_MULTIPROC_DIR` + hook `child_exit`).
   `/metrics` protegido por `METRICS_TOKEN` quando configurado.
3. **Tracing OpenTelemetry** (Django, psycopg, Redis, Celery) exportando OTLP/HTTP; o contexto
   atravessa o outbox, então requisição, entregas de eventos e o e-mail ficam num trace só.
   Desligado sem `OTEL_EXPORTER_OTLP_ENDPOINT`.
4. **Prontidão consulta os alarmes do RabbitMQ** (API de gerenciamento): alarme = broker
   indisponível, mesmo com a conexão ok.
5. **Local:** Prometheus, Grafana (fontes e painel versionados) e Jaeger num perfil `observability`
   do Compose. **Alertas como código** (`infra/observability/prometheus/alerts.yml`), validados com
   `promtool`, sem envio (Alertmanager) até existir destino real.

## Alternatives Considered

### Métricas por push (StatsD/OTLP metrics) em vez de pull

- Prós: sem endpoint para proteger; funciona com processos efêmeros.
- Contras: mais um agente; perde o "alvo caiu" que o pull dá de graça (`up == 0`).
- Por que não: com processos de longa duração, o pull do Prometheus é o padrão mais simples.

### Contadores para tudo (inclusive fila do outbox e e-mails)

- Contras: contador paralelo diverge da fonte da verdade (o banco) em reinício, rollback ou falha.
- Por que não: o que já está no banco é lido do banco na coleta, com consultas indexadas.

### Só `correlation_id`, sem tracing

- Prós: zero infraestrutura.
- Contras: não mostra onde o tempo foi gasto (qual consulta, qual task).
- Por que não: OTel com auto-instrumentação custa pouco e é desligável.

### Stack gerenciada (Datadog, New Relic, Grafana Cloud)

- Por que não agora: projeto local/portfólio; tudo em padrões abertos (Prometheus, OTLP) para
  trocar o destino sem mexer no código.

### Métricas de cache do `django-prometheus`

- Por que não: o wrapper exige o pacote `django-redis` (usamos o Redis nativo do Django); a
  prontidão já mede o Redis.

## Consequences

### Positivas

- Um `request_id` leva ao trace (Jaeger), aos logs do worker e ao registro de auditoria.
- Broker bloqueado vira prontidão 503, métrica 0 e alerta (`OrderflowDependencyDown`, verificado
  forçando o alarme de disco).
- Painel e alertas versionados: revisáveis em PR, iguais em qualquer máquina.

### Negativas / custos aceitos

- ~1,4 GB de imagens locais (só com o perfil); dependências OTel no backend.
- Cada coleta faz algumas consultas `COUNT` indexadas e checa as dependências (a cada 15 s).
- Multiprocesso exige diretório limpo a cada início (Dockerfile e Compose cuidam).
- Ações do sistema sem requisição de origem (Beat) têm `correlation_id` = id da task.

### Quando revisitar

Ao ir para um ambiente real: destino de alertas (Alertmanager), retenção de métricas/traces,
amostragem de traces e agregação de logs.
