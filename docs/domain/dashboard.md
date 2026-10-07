# Domínio: Dashboard (Indicadores)

> Implementado na Phase 11. Módulo **somente leitura** (sem models): `api/` → `application/` →
> `domain/` (períodos). Compõe leituras públicas de `orders`, `payments` e `inventory`; nenhum
> módulo depende dele. Cache: [ADR-014](../adr/014-dashboard-aggregate-cache.md).

## Pergunta que responde

"O que está acontecendo no negócio?" — sem gráfico que não tenha uma pergunta associada.

## Decisões de produto (Phase 11)

| Pergunta | Decisão | Por quê |
| --- | --- | --- |
| O que é faturamento? | **Pago menos estornado**: pagamentos aprovados no período (pela data de aprovação) menos estornos concluídos no período (pela data do estorno) | é o dinheiro que entrou de fato; pedido confirmado e não pago não é receita |
| Quem vê dinheiro? | Só com `reports:financial` (ADMIN, MANAGER, FINANCE) | permissão que já existia na matriz; os demais veem indicadores operacionais |
| Período | **Hoje, 7 e 30 dias**, comparados ao período anterior de mesmo tamanho | atalhos cobrem o uso diário; intervalo livre multiplicaria validação e variações de cache |
| Gráficos | **SVG próprio + tabela** | duas barras simples não justificam uma biblioteca; acessibilidade sob controle |

## Indicadores

| Indicador | Definição | Quem vê |
| --- | --- | --- |
| Pedidos recebidos | pedidos com `submitted_at` no período (rascunho não conta) | `orders:read` |
| Pedidos em andamento | retrato **atual** do funil (`PENDING` … `SHIPPED`), independente do período | `orders:read` |
| Pedidos recentes | 5 últimos enviados (com total — dado do pedido, como na lista) | `orders:read` |
| Faturamento líquido | aprovado − estornado no período; pagamento estornado depois **conta na data em que foi pago** e o estorno sai na data dele | `reports:financial` |
| Estornos | estornos concluídos no período | `reports:financial` |
| Ticket médio | aprovado ÷ nº de pagamentos aprovados no período (vazio sem pagamentos) | `reports:financial` |
| Estoque baixo | itens com `available ≤ reorder_point` (`reorder_point > 0`) — mesma regra do filtro da tela de estoque | `inventory:read` |
| Gráfico | faturamento líquido por hora (hoje) ou dia; sem `reports:financial`, pedidos recebidos | conforme acima |

## Períodos (`domain/periods.py`)

- Todo período termina **agora** e começa à meia-noite do fuso do negócio
  (`BUSINESS_TIME_ZONE`, America/Sao_Paulo) de N−1 dias atrás; o banco continua em UTC.
- O período anterior é o mesmo intervalo deslocado N dias: "hoje até as 15h" compara com "ontem
  até as 15h" (comparar com o dia de ontem inteiro faria hoje parecer sempre pior).
- Barras vazias aparecem (zero), e o rótulo é o dia/hora do negócio como o backend mandou — o
  frontend não converte para o fuso do navegador (mudaria o dia).
- Variação sem base (anterior zerado) não mostra direção nem cor: "sem comparação".

## Desempenho e cache

Medição e decisão no [ADR-014](../adr/014-dashboard-aggregate-cache.md): três índices
(`orders_org_submitted_idx`, `payments_org_revenue_idx`, `payments_org_refunded_idx`, criados com
`CONCURRENTLY`) levaram 220–250 ms para 35–61 ms numa organização com 200 mil pedidos; o cache de
60 s por organização + período limita a carga a ~1 cálculo por minuto, qualquer que seja o número
de pessoas com a tela aberta. A permissão é aplicada **depois** do cache.

## API

| Endpoint | Permissão | Resposta |
| --- | --- | --- |
| `GET /api/v1/dashboard?period=today\|7d\|30d` (padrão `7d`) | `orders:read` | `orders` sempre; `money` e `stock` `null` sem a permissão; `generated_at` (quando foi calculado) |

## Questões em aberto

- Intervalo livre de datas e exportação (relatórios, Phase futura).
- Vendas por cliente/produto/vendedor; metas.
- Agregados materializados se a consulta direta passar de ~500 ms (ADR-014).
