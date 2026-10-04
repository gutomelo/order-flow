import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'

import * as suppliersApi from '@/modules/suppliers/api/suppliersApi'
import type { SupplierFilters, SupplierInput } from '@/modules/suppliers/types'

export const suppliersKeys = {
  all: ['suppliers'] as const,
  list: (filters: SupplierFilters) => [...suppliersKeys.all, 'list', filters] as const,
  options: () => [...suppliersKeys.all, 'options'] as const,
}

export function useSuppliersList(filters: MaybeRefOrGetter<SupplierFilters>) {
  return useQuery({
    queryKey: computed(() => suppliersKeys.list(toValue(filters))),
    queryFn: () => suppliersApi.listSuppliers(toValue(filters)),
    placeholderData: keepPreviousData,
  })
}

export function useSupplierOptions() {
  return useQuery({
    queryKey: suppliersKeys.options(),
    queryFn: suppliersApi.listActiveSupplierOptions,
  })
}

export function useSaveSupplier() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: { id?: string; data: SupplierInput }) =>
      input.id
        ? suppliersApi.updateSupplier(input.id, input.data)
        : suppliersApi.createSupplier(input.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: suppliersKeys.all }),
  })
}

export function useSetSupplierActive() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: { id: string; active: boolean }) =>
      suppliersApi.setSupplierActive(input.id, input.active),
    // Produtos exibem o fornecedor padrão: também ficam desatualizados.
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: suppliersKeys.all }),
        queryClient.invalidateQueries({ queryKey: ['products'] }),
      ]),
  })
}
