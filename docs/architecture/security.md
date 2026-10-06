# Segurança

Princípio: **o backend é a autoridade**. O frontend esconde o que o usuário não pode fazer apenas
por UX; toda requisição é validada e autorizada no servidor.

## Autenticação

JWT com SimpleJWT (ADR-007): access token curto em memória no frontend; refresh token rotativo com
blacklist em cookie `HttpOnly; Secure; SameSite=Strict` restrito ao path de refresh; logout invalida
o refresh. Senhas com o hasher padrão do Django (PBKDF2/Argon2 se adotado), validadores de senha
habilitados. Throttling em login e refresh.

## Autorização — RBAC centralizado

Permissões no formato `resource:action`, definidas em **um** catálogo (`apps/identity`), atribuídas
a roles. Verificação por uma única porta:

```python
class OrderViewSet(...):
    permission_classes = [IsAuthenticated, HasPermission("orders:read")]

    @action(detail=True, methods=["post"],
            permission_classes=[IsAuthenticated, HasPermission("orders:cancel")])
    def cancel(self, request, pk=None): ...
```

Proibido: `if user.role == "ADMIN"` espalhado. Regras de escopo de objeto (ex.: "SALES vê apenas
clientes da sua equipe") ficam em políticas por módulo aplicadas no `get_queryset`.

### Matriz inicial

| Permissão | ADMIN | MANAGER | SALES | WAREHOUSE | FINANCE | VIEWER |
| --- | --- | --- | --- | --- | --- | --- |
| `customers:read` | ✓ | ✓ | ✓ | | ✓ | ✓ |
| `customers:create` / `customers:update` | ✓ | ✓ | ✓ | | | |
| `customers:manage_segments` | ✓ | ✓ | | | | |
| `suppliers:read` | ✓ | ✓ | | ✓ | ✓ | ✓ |
| `suppliers:manage` | ✓ | ✓ | | | | |
| `catalog:read` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `catalog:manage` | ✓ | ✓ | | | | |
| `pricing:read` | ✓ | ✓ | ✓ | | ✓ | ✓ |
| `pricing:manage` | ✓ | ✓ | | | | |
| `inventory:read` | ✓ | ✓ | ✓ | ✓ | | ✓ |
| `inventory:update` (recebimento, transferência) | ✓ | ✓ | | ✓ | | |
| `inventory:adjust` | ✓ | ✓ | | ✓ | | |
| `orders:read` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `orders:create` | ✓ | ✓ | ✓ | | | |
| `orders:cancel` | ✓ | ✓ | ✓ | | | |
| `orders:cancel_paid` | ✓ | ✓ | | | ✓ | |
| `orders:process` (separação) | ✓ | ✓ | | ✓ | | |
| `orders:ship` | ✓ | ✓ | | ✓ | | |
| `payments:read` | ✓ | ✓ | | | ✓ | |
| `payments:create` | ✓ | ✓ | ✓ | | ✓ | |
| `payments:refund` | ✓ | | | | ✓ | |
| `reports:financial` | ✓ | ✓ | | | ✓ | |
| `users:manage` | ✓ | | | | | |
| `audit:read` | ✓ | ✓ | | | | |

Mudanças de role/permissão de usuário geram `AuditLog` `USER_PERMISSION_CHANGED`.
A matriz é testada (teste parametrizado por role × endpoint).

## Isolamento entre organizações (multi-tenancy)

Regra mais importante de segurança do produto ([ADR-013](../adr/013-multi-tenancy.md)):

- O tenant vem **sempre** de `request.user.organization_id` — nunca de header, URL, corpo ou JWT.
- Views de negócio usam `shared.tenancy.TenantScopedQuerysetMixin`; use cases recebem
  `organization_id` no command e filtram por ele.
- Objeto de outra organização → **404**.
- Teste de arquitetura garante que todo model de `apps/` tem `organization`; testes de API de cada
  recurso incluem acesso cruzado entre organizações.
- Escopo dentro da organização: SALES vê todos os clientes e pedidos da própria organização
  (decisão de produto); equipes não restringem visibilidade.

## IDOR

- `get_queryset()` sempre escopado à organização e ao que o usuário pode ver; objetos fora do escopo retornam
  **404** (não 403, para não revelar existência).
- IDs públicos são UUIDs (não enumeráveis); números legíveis (`Order.number`) não são usados como
  chave de acesso na API.
- Testes de API incluem acesso a objeto de outro escopo.
- Recursos aninhados (`/customers/{id}/addresses/{address_id}`) filtram pela organização **e** pelo
  pai da URL: o endereço de outro cliente responde 404 mesmo com um ID válido.

## Mass assignment e validação

- Serializers de escrita com `fields` explícitos; campos de servidor (`status`, `total`,
  `reserved`, `created_by`, roles) sempre read-only ou ausentes.
- Totais e preços **nunca** aceitos do cliente: são calculados no domínio.
- Validação server-side de tipos, limites e formatos (quantidade > 0, decimais com 2 casas, CNPJ).
- Somente ORM/queries parametrizadas.

## Uploads (quando existirem)

Validação de tipo por conteúdo e tamanho, nomes gerados pelo servidor, armazenamento fora do
diretório servido, nunca executar/servir com o content-type informado pelo cliente.

## Rate limiting

Throttling do DRF com Redis: global por usuário/IP + escopos específicos para `auth` (login/refresh),
criação de pedidos e pagamentos. Excesso → `429 RATE_LIMITED`.

## CORS, CSRF e headers

- CORS restrito às origens do frontend configuradas por ambiente (`django-cors-headers`),
  `CORS_ALLOW_CREDENTIALS` apenas para o endpoint de refresh por cookie.
- Endpoint de refresh por cookie protegido por `SameSite=Strict` + verificação de origem.
- Produção: `DEBUG=False`, `ALLOWED_HOSTS` explícito, `SECURE_SSL_REDIRECT`, HSTS,
  `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS="DENY"`, `Referrer-Policy`, cookies `Secure`;
  CSP no servidor que entrega o frontend. `manage.py check --deploy` sem alertas.

## Implementação (Phase 2)

| Peça | Onde |
| --- | --- |
| Catálogo de permissões e política papel → permissões | `apps/identity/domain/permissions.py` (teste compara com a matriz acima) |
| Porta de autorização das views | `shared.permissions.HasPermission("resource:action")` |
| Escopo por organização | `shared.tenancy` (`TenantScopedModel`, `TenantScopedQuerysetMixin`) |
| Autenticação por requisição | `OrganizationAwareJWTAuthentication` (usuário e organização ativos) |
| Teste de arquitetura de tenancy | `backend/tests/architecture/test_tenant_scoping.py` |

## Secrets

Somente variáveis de ambiente. `.env` no `.gitignore`; `.env.example` versionado com nomes e valores
fictícios. Nenhum secret em Dockerfile, compose versionado com valores reais, logs ou respostas.

## Dados sensíveis em logs e erros

Nunca registrar senha, JWT, refresh token, header `Authorization`, dados de cartão, secrets.
Dados pessoais (LGPD) — nome, e-mail e telefone de contatos de clientes — também não vão para logs:
os eventos registram apenas IDs (`customers.contact.created`, `contact_id=...`).
O processador de logs (`shared/logging`) remove chaves sensíveis conhecidas como defesa adicional.
Erros 500 retornam mensagem genérica com `request_id`; detalhes apenas no log.

## Pagamentos

O OrderFlow **não armazena dados de cartão**. O `PaymentGateway` trabalha com tokens/IDs do
provedor; o `FakePaymentGateway` simula aprovação, recusa, timeout, indisponibilidade e estorno
recusado (`docs/domain/payments.md`).

- O `card_token` é `write_only` no serializer, repassado ao gateway e **nunca** persistido nem
  logado (teste `test_card_token_is_never_stored` procura o token no banco e na resposta).
- Cobrar e estornar exigem `Idempotency-Key` (ADR-012); a cobrança usa o modo de várias
  transações para não cobrar duas vezes num reenvio.
- **Cancelar pedido pago** exige `orders:cancel_paid` (MANAGER, FINANCE, ADMIN): a permissão
  depende do estado do pedido, então a regra está numa política do domínio
  (`orders.domain.policies.permission_to_cancel`), não espalhada em `if`s.
- Estornos (`payments:refund`) só para FINANCE e ADMIN; a listagem financeira exige
  `payments:read`. Tudo escopado por organização (anti-IDOR).

## Revisão

Toda mudança em auth, permissões, endpoints, serializers, settings ou dependências passa pela skill
`review-security` (agent `security-reviewer`) antes do merge.
