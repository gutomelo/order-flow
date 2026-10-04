# Documentação de domínio

Fonte da verdade das **regras de negócio**. O código implementa o que está aqui; divergência entre
código e documento é um defeito (de um dos dois). Atualize o documento no mesmo PR que muda a regra.

| Documento | Conteúdo | Status |
| --- | --- | --- |
| [glossary.md](glossary.md) | Linguagem ubíqua PT ↔ EN (nomes usados no código) | Vigente |
| [identity.md](identity.md) | Organizações (tenants), usuários, equipes, papéis, permissões, autenticação | Vigente |
| [catalog.md](catalog.md) | Produtos (SKU, GTIN, unidade), categorias hierárquicas, por que o produto não tem preço | Vigente |
| [suppliers.md](suppliers.md) | Fornecedores, CNPJ numérico e alfanumérico | Vigente |
| [orders.md](orders.md) | Ciclo de vida do pedido, máquina de estados, totais, cancelamento, devolução | Vigente |
| [inventory.md](inventory.md) | Saldo, reservas, movimentações, concorrência, expiração | Vigente |

Documentos a criar nas fases correspondentes (template `.claude/templates/domain-doc.md`):
`customers.md` (Phase 5), `pricing.md` (Phase 6),
`payments.md` (Phase 8), `shipping.md` (Phase 9), `notifications.md` (Phase 10), `audit.md` (Phase 12).

A visão geral dos módulos, suas fronteiras e dependências está em
[../architecture/domain-model.md](../architecture/domain-model.md).
