# Glossário — linguagem ubíqua

Todo identificador de código usa o termo da coluna **Código**. A documentação pode usar o termo em
português, mas ao citar código usa o nome exato. Termos novos entram aqui no mesmo PR.

## Organização e acesso

| Português | Código | Definição |
| --- | --- | --- |
| Organização | `Organization` | Empresa cliente do SaaS (tenant); todo dado de negócio pertence a uma |
| Usuário | `User` | Pessoa que acessa o sistema; pertence a uma organização |
| Equipe | `Team` | Agrupamento de usuários (ex.: equipe comercial Sul) |
| Papel | `Role` | Conjunto nomeado de permissões (`ADMIN`, `MANAGER`, `SALES`, `WAREHOUSE`, `FINANCE`, `VIEWER`) |
| Permissão | `Permission` | Capacidade `resource:action` (ex.: `orders:cancel`) |
| Registro de auditoria | `AuditLog` | Registro imutável de operação relevante |

## Comercial

| Português | Código | Definição |
| --- | --- | --- |
| Cliente | `Customer` | Empresa compradora (B2B), identificada por CNPJ (`tax_id`) |
| Fornecedor | `Supplier` | Empresa que fornece produtos |
| Produto | `Product` | Item vendável identificado por `sku` |
| Categoria | `Category` | Classificação hierárquica de produtos |
| Tabela de preço | `PriceList` | Preços aplicáveis a um segmento/contrato |
| Política de preço | `PricingStrategy` | Regra que calcula o preço unitário (padrão, atacado, contrato) |
| Desconto | `Discount` / `DiscountPolicy` | Redução aplicada a linha ou pedido |
| Dinheiro | `Money` | Valor `Decimal` + moeda (`BRL`) |

## Pedidos

| Português | Código | Definição |
| --- | --- | --- |
| Pedido | `Order` | Intenção de compra de um cliente com ciclo de vida próprio |
| Número do pedido | `Order.number` | Identificador legível e sequencial (`OF-2026-000123`); o ID técnico é UUID |
| Item do pedido | `OrderLine` | Produto, quantidade e preço congelado no momento da submissão |
| Status do pedido | `OrderStatus` | Estado no ciclo de vida (ver `orders.md`) |
| Histórico de status | `OrderStatusHistory` | Registro de cada transição (de, para, quem, quando, motivo) |
| Rascunho | `DRAFT` | Pedido editável, sem preço congelado nem reserva |
| Submeter pedido | `PlaceOrder` / `SubmitOrder` | Confirmar comercialmente o pedido |
| Cancelamento | `CancelOrder` | Encerrar o pedido antes do envio |
| Devolução | `OrderReturn` | Retorno de mercadoria após entrega |
| Separação | `PROCESSING` / `StartPicking` | Coleta física dos itens no depósito |

## Estoque

| Português | Código | Definição |
| --- | --- | --- |
| Depósito | `Warehouse` | Local físico de armazenagem |
| Item de estoque | `StockItem` | Saldo de um produto em um depósito |
| Quantidade física | `on_hand` | Unidades fisicamente no depósito |
| Quantidade reservada | `reserved` | Unidades comprometidas com pedidos ainda não enviados |
| Quantidade disponível | `available` | `on_hand - reserved`; o que pode ser vendido |
| Reserva de estoque | `StockReservation` | Compromisso de unidades para uma linha de pedido, com validade |
| Movimentação de estoque | `StockMovement` | Registro imutável de toda alteração de saldo |
| Ponto de reposição | `reorder_point` | Limite abaixo do qual o item é "estoque baixo" |
| Ajuste de inventário | `ADJUSTMENT` | Correção manual de `on_hand` com motivo obrigatório |
| Transferência | `TRANSFER` | Movimento entre depósitos |

## Financeiro e logística

| Português | Código | Definição |
| --- | --- | --- |
| Pagamento | `Payment` | Tentativa de cobrança de um pedido |
| Estorno / reembolso | `Refund` | Devolução total ou parcial de um pagamento |
| Gateway de pagamento | `PaymentGateway` | Porta para o provedor de pagamento (adapter) |
| Envio / remessa | `Shipment` | Despacho físico de um pedido |
| Transportadora / provedor de frete | `ShippingProvider` | Porta para o provedor logístico (adapter) |
| Código de rastreio | `tracking_code` | Identificador do envio no provedor |

## Técnico

| Português | Código | Definição |
| --- | --- | --- |
| Evento de domínio | `DomainEvent` | Fato ocorrido no domínio, nome no passado (`OrderCreated`) |
| Caso de uso | use case (`PlaceOrder`) | Operação da application layer com uma intenção de negócio |
| Chave de idempotência | `Idempotency-Key` / `IdempotencyRecord` | Garante mesmo resultado para requisições repetidas |
| Caixa de saída | `OutboxEvent` | Evento persistido para publicação confiável (ADR-011) |
| ID de requisição | `request_id` | Identificador único de uma requisição HTTP |
| ID de correlação | `correlation_id` | Identificador que acompanha um fluxo entre requisição, eventos e tasks |
