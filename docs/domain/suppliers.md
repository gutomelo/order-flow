# Domínio: Suppliers (Fornecedores)

> Implementado na Phase 3. Módulo simples (nível 1 do template de módulos).

## Responsabilidade

Cadastro das empresas que fornecem produtos. Nesta fase o fornecedor é referência cadastral
(fornecedor padrão do produto); compras e recebimentos chegam com `inventory`.

## Modelo

| Campo | Regra |
| --- | --- |
| `legal_name` | razão social, obrigatória |
| `trade_name` | nome fantasia, opcional |
| `tax_id` | CNPJ, obrigatório, **válido** e único por organização (armazenado sem máscara) |
| `email`, `phone` | contatos opcionais |
| `is_active` | inativação no lugar de exclusão |

## CNPJ alfanumérico

A partir de julho de 2026 a Receita Federal emite CNPJs **alfanuméricos** (IN RFB nº 2.229/2024):
as 12 primeiras posições aceitam letras maiúsculas e dígitos; os 2 dígitos verificadores continuam
numéricos. O cálculo do módulo 11 usa o valor de cada caractere como `código ASCII − 48`
(dígitos mantêm seu valor; `A` = 17, `B` = 18, …).

O validador fica em `shared/domain/documents.py`, porque o mesmo documento identifica clientes
(Phase 5). Ele aceita os dois formatos, com ou sem máscara, e normaliza para 14 caracteres
maiúsculos sem pontuação.

## Regras

| # | Regra | Garantida em |
| --- | --- | --- |
| S1 | CNPJ válido (numérico ou alfanumérico) | serviço (validador compartilhado) |
| S2 | CNPJ único por organização | UNIQUE (`organization_id`, `tax_id`) |
| S3 | Fornecedor não é excluído: é inativado; produtos mantêm a referência | serviço |
| S4 | Fornecedor inativo não pode ser atribuído como padrão de um produto | regra C4 do catálogo |

## Casos de uso

| Use case | Endpoint | Permissão |
| --- | --- | --- |
| Listar/buscar | `GET /api/v1/suppliers?search=&is_active=` | `suppliers:read` |
| Criar | `POST /api/v1/suppliers` | `suppliers:manage` |
| Editar | `PATCH /api/v1/suppliers/{id}` | `suppliers:manage` |
| Ativar/inativar | `POST /api/v1/suppliers/{id}/activate` · `/deactivate` | `suppliers:manage` |

## Erros de domínio

| Código | HTTP | Quando |
| --- | --- | --- |
| `INVALID_TAX_ID` | 422 | CNPJ com formato ou dígitos verificadores inválidos |
| `TAX_ID_ALREADY_IN_USE` | 409 | CNPJ já cadastrado na organização |
