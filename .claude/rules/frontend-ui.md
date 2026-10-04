---
paths:
  - "frontend/src/**/*.vue"
  - "frontend/src/**/*.css"
---

# UI, UX e acessibilidade

- **Sem hexadecimal em componentes.** Use apenas tokens semânticos (`var(--color-primary)`,
  `--color-surface`, `--color-text-secondary`, ...) definidos em `src/app/styles/tokens.css`.
  Tokens preparados para dark mode.
- Fonte: `Inter, ui-sans-serif, system-ui, sans-serif`.
- Estética SaaS B2B (Linear, Stripe, GitHub, Shopify Admin, Vercel como referência de
  hierarquia/densidade — nunca copiar). Evitar gradientes, glassmorphism, sombras pesadas,
  animações sem função.
- Toda operação assíncrona mostra **loading, success e error**. Botões de submit desabilitam
  durante o envio (anti double-submit).
- Ações destrutivas exigem diálogo de confirmação com texto específico ("Cancelar pedido #1234?").
- Empty states explicam o porquê e o próximo passo ("Nenhum pedido encontrado. Crie o primeiro
  pedido ou ajuste os filtros.").
- Tabelas: paginação, busca, filtros, ordenação, skeleton no loading, empty e error state.
- Status nunca só por cor: badge = ícone + texto + cor (componente `StatusBadge` único).
- Formulários: `<label>` associado, help text quando necessário, erro inline com
  `aria-describedby`, foco no primeiro campo inválido.
- Acessibilidade WCAG 2.2 AA: contraste, navegação por teclado, `:focus-visible` visível,
  HTML semântico, ARIA só quando o HTML nativo não basta.
- Desktop-first responsivo: sidebar recolhível (vira drawer no mobile); tabelas com scroll
  horizontal ou layout alternativo em telas pequenas.
