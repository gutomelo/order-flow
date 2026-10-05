import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'

import * as api from '@/modules/pricing/api/pricingApi'
import type { PriceItemFilters } from '@/modules/pricing/types'

export const pricingKeys = {
  all: ['pricing'] as const,
  lists: () => [...pricingKeys.all, 'lists'] as const,
  list: (id: string) => [...pricingKeys.all, 'list', id] as const,
  items: (id: string, filters: PriceItemFilters) =>
    [...pricingKeys.list(id), 'items', filters] as const,
}

export function usePriceLists() {
  return useQuery({ queryKey: pricingKeys.lists(), queryFn: api.listPriceLists })
}

export function usePriceList(id: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => pricingKeys.list(toValue(id))),
    queryFn: () => api.getPriceList(toValue(id)),
  })
}

export function usePriceItems(
  id: MaybeRefOrGetter<string>,
  filters: MaybeRefOrGetter<PriceItemFilters>,
) {
  return useQuery({
    queryKey: computed(() => pricingKeys.items(toValue(id), toValue(filters))),
    queryFn: () => api.listPriceItems(toValue(id), toValue(filters)),
    placeholderData: keepPreviousData,
  })
}

/**
 * Invalida `pricing` e as prévias de pedidos: um preço novo muda a cotação dos rascunhos.
 * `onSettled` também no erro — um 409 indica que a tela estava desatualizada.
 */
function usePricingMutation<Input, Output>(mutationFn: (input: Input) => Promise<Output>) {
  const queryClient = useQueryClient()
  return useMutation({
    // Wrapper: o TanStack passa um 2º argumento (contexto) que não pertence à API.
    mutationFn: (input: Input) => mutationFn(input),
    onSettled: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: pricingKeys.all }),
        queryClient.invalidateQueries({ queryKey: ['orders', 'quote'] }),
      ]),
  })
}

export const useSavePriceList = () =>
  usePricingMutation((input: { id?: string; name: string; segment_id: string | null }) =>
    input.id ? api.renamePriceList(input.id, input.name) : api.createPriceList(input),
  )

export const useDeletePriceList = () => usePricingMutation((id: string) => api.deletePriceList(id))

export const useSavePriceItem = (priceListId: string) =>
  usePricingMutation((input: { id?: string; product_id?: string; unit_price: string }) =>
    api.savePriceItem(priceListId, input, input.id),
  )

export const useRemovePriceItem = (priceListId: string) =>
  usePricingMutation((id: string) => api.removePriceItem(priceListId, id))
