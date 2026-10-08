# ADR-007: Autenticação JWT com SimpleJWT, rotação e blacklist

- **Status:** Accepted
- **Data:** 2026-10-04
- **Relacionados:** ADR-003, `docs/architecture/security.md`

## Context

O frontend é uma SPA (Vue) consumindo uma API REST stateless. Precisamos de autenticação que
funcione bem com SPA, permita logout efetivo, limite o impacto de token vazado e não exponha
credenciais de longa duração a JavaScript.

## Decision

Usar **JWT via djangorestframework-simplejwt** com:

- **Access token** de vida curta (padrão 10 min), enviado em `Authorization: Bearer`.
  No frontend fica **somente em memória** (store de sessão), nunca em `localStorage`.
- **Refresh token** de vida maior (padrão 7 dias) com **rotação** (`ROTATE_REFRESH_TOKENS=True`) e
  **blacklist** (`BLACKLIST_AFTER_ROTATION=True`, app `token_blacklist`).
- Refresh token transportado em **cookie `HttpOnly`, `Secure`, `SameSite=Strict`**, com `path`
  restrito ao endpoint de refresh — inacessível a JavaScript (mitiga roubo via XSS). Exige views de
  login/refresh/logout customizadas sobre as do SimpleJWT.
- **Logout** coloca o refresh token na blacklist e limpa o cookie.
- Reuso de refresh token já rotacionado é rejeitado (indicador de vazamento).
- Throttling em login e refresh. Claims mínimas no access token (`user_id`, `jti`); permissões são
  resolvidas no servidor, não confiadas a claims.

Endpoints: `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout`,
`GET /api/v1/auth/me`.

## Alternatives Considered

### Sessão Django + cookie (SessionAuthentication)

- Prós: revogação imediata, CSRF nativo, simples.
- Contras: acoplamento ao mesmo domínio; menos alinhado ao requisito de API stateless e a clientes
  não-browser futuros.
- Por que não: requisito do projeto é JWT; o modelo híbrido (access em memória + refresh em cookie
  HttpOnly) captura boa parte da segurança das sessões.

### JWT com ambos os tokens em `localStorage`

- Por que não: qualquer XSS rouba credenciais de longa duração.

### OAuth2/OIDC com provedor externo

- Por que não agora: complexidade desnecessária para o MVP; pode ser adicionado depois (SSO B2B).

## Consequences

### Positivas

- Access token vazado expira rápido; refresh inacessível a JS; logout efetivo via blacklist.

### Negativas / custos aceitos

- Access token não é revogável antes de expirar (janela de até 10 min).
- Views customizadas para cookie; tabela de blacklist cresce (limpeza periódica com
  `flushexpiredtokens` via Celery Beat).
- Cookie com `SameSite=Strict` exige frontend e API no mesmo site (configuração de deploy).

### Quando revisitar

Requisito de SSO corporativo, apps mobile nativos ou revogação instantânea de acesso.
