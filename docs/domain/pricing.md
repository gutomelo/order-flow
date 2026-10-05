# Domínio: Pricing (Preços)

> Implementado na Phase 6 ("pricing básico"). Módulo de complexidade baixa: `models.py`,
> `services.py`, `selectors.py`, `api/`.

## Responsabilidade

Responder **"quanto custa este produto para este cliente?"**. O catálogo diz o que o produto é
(`catalog.md` explica por que o produto não tem preço); `orders` pede a cotação e congela o valor
no pedido. `pricing` não conhece pedidos.

## Modelo

| Entidade | Campos | Observação |
| --- | --- | --- |
| `PriceList` | `name`, `segment` (opcional), `currency` | sem segmento = **tabela padrão** da organização |
| `PriceListItem` | `price_list`, `product`, `unit_price` | `NUMERIC(14,2)`, em BRL |

## Regra de resolução do preço

Para um cliente com segmento `S`:

1. item do produto na tabela do segmento `S` (se a tabela existir e tiver o produto);
2. senão, item do produto na tabela padrão;
3. senão, o produto **não pode ser vendido** para esse cliente (`PRICE_NOT_FOUND`).

Cliente sem segmento usa só a tabela padrão. A cotação informa a origem (`SEGMENT` ou `DEFAULT`),
que o pedido guarda junto com o preço.

### Por que não um Strategy agora

`CLAUDE.md` prevê Strategy em `pricing` "onde o comportamento realmente varia" (contrato, atacado
por volume). Nesta fase a regra é uma busca com fallback, sem variação de comportamento: uma função
resolve. Quando surgir a segunda forma de calcular (ex.: desconto por volume), a função vira a
estratégia padrão e as demais entram ao lado dela — a interface pública (`quote_prices`) não muda.

### Por que tabelas por segmento e não desconto percentual

Preço por produto e segmento expressa acordos reais de B2B ("para Atacado, o refrigerante custa
R$ 2,90"), que um percentual único não expressa. O custo é manter mais itens; a tabela padrão
continua sendo o fallback, então a tabela do segmento só precisa dos produtos com preço diferente.

## Regras

| # | Regra | Garantida em |
| --- | --- | --- |
| PR1 | No máximo **uma** tabela padrão por organização e **uma** tabela por segmento | UNIQUE parcial |
| PR2 | Nome da tabela único na organização | UNIQUE |
| PR3 | Um produto aparece no máximo uma vez por tabela | UNIQUE (`price_list_id`, `product_id`) |
| PR4 | `unit_price >= 0` com 2 casas decimais | serializer + CHECK |
| PR5 | Só produtos ativos e segmentos ativos podem ser associados | serviço |
| PR6 | Alterar ou remover preços **não** altera pedidos já submetidos (o pedido guarda cópia) | `orders` (snapshot) |
| PR7 | A tabela de um segmento não muda de segmento depois de criada | serviço (só o nome é editável) |

## Interface pública para outros módulos

| Função | Uso |
| --- | --- |
| `selectors.quote_prices(organization_id, segment_id, product_ids)` | `orders` cota as linhas (rascunho, submissão, prévia) |

## Casos de uso

| Use case | Endpoint | Permissão |
| --- | --- | --- |
| Listar tabelas | `GET /api/v1/price-lists` | `pricing:read` |
| Criar/renomear/remover tabela | `POST /api/v1/price-lists` · `PATCH`/`DELETE /{id}` | `pricing:manage` |
| Listar itens (busca por SKU/nome) | `GET /api/v1/price-lists/{id}/items?search=` | `pricing:read` |
| Incluir/alterar/remover item | `POST .../items` · `PATCH`/`DELETE .../items/{item_id}` | `pricing:manage` |

Remover uma tabela remove seus itens; pedidos já submetidos não são afetados (PR6). Rascunhos são
recotados na próxima edição ou na submissão.

## Erros de domínio

| Código | HTTP | Quando |
| --- | --- | --- |
| `PRICE_NOT_FOUND` | 422 | Produto sem preço na tabela do segmento nem na padrão (`details.product_ids`) |
| `PRICE_LIST_NAME_ALREADY_IN_USE` | 409 | Nome repetido |
| `PRICE_LIST_ALREADY_EXISTS` | 409 | Já existe tabela padrão / tabela para o segmento (`details.field = segment_id`) |
| `SEGMENT_NOT_AVAILABLE` | 422 | Segmento inexistente ou inativo |
| `PRODUCT_NOT_AVAILABLE` | 422 | Produto inexistente ou inativo |
| `PRICE_ITEM_ALREADY_EXISTS` | 409 | Produto já está na tabela (`details.field = product_id`) |

## Fora do escopo

Descontos (por volume, por pedido, cupons), vigência de preços (início/fim), preços por contrato
de cliente e importação em massa (CSV).
