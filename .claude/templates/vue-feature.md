# Template: feature Vue

```text
src/modules/<feature>/
├── api/
│   └── <feature>Api.ts         # funções HTTP tipadas (usam src/services/http)
├── composables/
│   ├── <feature>Keys.ts        # query keys centralizadas
│   ├── use<Feature>List.ts     # useQuery
│   └── useCreate<Feature>.ts   # useMutation + invalidação
├── components/                 # componentes específicos da feature
├── pages/
│   ├── <Feature>ListPage.vue
│   └── <Feature>DetailPage.vue
├── schemas/
│   └── <feature>Form.ts        # Zod
├── types/
│   └── index.ts
├── routes.ts                   # rotas da feature (lazy-loaded)
└── tests/
```

Crie só o que a feature usa.

## Query keys

```ts
export const ordersKeys = {
  all: ['orders'] as const,
  lists: () => [...ordersKeys.all, 'list'] as const,
  list: (filters: OrderFilters) => [...ordersKeys.lists(), filters] as const,
  detail: (id: string) => [...ordersKeys.all, 'detail', id] as const,
}
```

## Query

```ts
export function useOrderList(filters: MaybeRefOrGetter<OrderFilters>) {
  return useQuery({
    queryKey: computed(() => ordersKeys.list(toValue(filters))),
    queryFn: () => ordersApi.list(toValue(filters)),
    placeholderData: keepPreviousData,
  })
}
```

## Mutation com idempotência

```ts
export function useCancelOrder() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: { id: string; reason: string }) => ordersApi.cancel(input),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: ordersKeys.lists() })
      queryClient.invalidateQueries({ queryKey: ordersKeys.detail(id) })
    },
  })
}
```

Para criação de pedido/pagamento: gerar `Idempotency-Key` (`crypto.randomUUID()`) **uma vez por
intenção** (ao abrir o formulário/confirmar), reutilizar em retries da mesma intenção.

## Checklist da página

- [ ] Loading (skeleton), empty state com próximo passo, error state com ação de tentar novamente
- [ ] Filtros/busca/ordenação refletidos na URL (query params)
- [ ] Textos via i18n; datas e moeda formatadas em pt-BR
- [ ] Ações destrutivas com confirmação; feedback de sucesso/erro
- [ ] Acessível por teclado; status com ícone + texto
- [ ] Rotas protegidas por permissão (UX) — backend continua sendo a autoridade
- [ ] Testes de composables/schemas/componentes com lógica
