# Idioma do projeto (obrigatório)

- **Código em inglês, sempre**: classes, funções, variáveis, enums, eventos, tabelas, colunas,
  arquivos, diretórios, rotas, códigos de erro, chaves de i18n, nomes de tarefas Celery e Moon.
  - Correto: `StockReservation`, `reserve_stock()`, `INSUFFICIENT_STOCK`, `/api/v1/orders/{id}/cancel`
  - Incorreto: `ReservaEstoque`, `reservar_estoque()`, `ESTOQUE_INSUFICIENTE`, `/pedidos`
- **Comentários de código** podem ser em português. Explique o *porquê*, nunca repita o código.
- **Documentação interna** (`docs/`, ADRs, CLAUDE.md, agents, skills) predominantemente em português.
- **Interface do usuário** em pt-BR, sempre via i18n (nunca string literal visível em componente).
- **Mensagens de erro da API**: `code` em inglês (`SCREAMING_SNAKE_CASE`), `message` em pt-BR.
- **Commits** seguem Conventional Commits; a descrição pode ser em inglês (preferido) ou português,
  mas tipo e escopo são sempre em inglês.
- Traduções de termos de negócio: use `docs/domain/glossary.md`. Se um termo novo surgir,
  adicione-o ao glossário no mesmo PR.
