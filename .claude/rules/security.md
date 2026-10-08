# Segurança (sempre carregada)

- Nunca confiar no frontend: toda validação e autorização acontece no backend.
- Autorização via permissões `resource:action` centralizadas (`shared/permissions` +
  `apps/identity`). Proibido `if user.role == "..."` fora da política central.
- Toda busca de objeto por ID passa por queryset **já escopado** ao que o usuário pode ver (anti-IDOR).
- Serializers de escrita declaram campos explicitamente (`fields = [...]`, nunca `__all__`);
  campos como `status`, `total`, `created_by`, `reserved` são read-only (anti mass assignment).
- Somente ORM / queries parametrizadas. `raw()`/`extra()`/SQL manual exigem justificativa e revisão.
- Nunca logar: senhas, tokens JWT, refresh tokens, `Authorization` header, dados de cartão, secrets.
- Erros para o cliente nunca expõem stack trace, SQL, paths, nomes de tabelas ou secrets.
- Secrets só via variáveis de ambiente; `.env` nunca é versionado; `.env.example` sem valores reais.
- Endpoints sensíveis (login, refresh, criação de pedido, pagamento) têm throttling.
- Novas dependências: preferir pacotes mantidos; justificar no PR.
