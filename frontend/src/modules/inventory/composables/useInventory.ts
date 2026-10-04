import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'

import * as inventoryApi from '@/modules/inventory/api/inventoryApi'
import type { MovementFilters, StockFilters } from '@/modules/inventory/types'

export const inventoryKeys = {
  all: ['inventory'] as const,
  warehouses: () => [...inventoryKeys.all, 'warehouses'] as const,
  stock: (filters: StockFilters) => [...inventoryKeys.all, 'stock', filters] as const,
  movements: (filters: MovementFilters) => [...inventoryKeys.all, 'movements', filters] as const,
}

export function useWarehouses() {
  return useQuery({ queryKey: inventoryKeys.warehouses(), queryFn: inventoryApi.listWarehouses })
}

export function useStockList(filters: MaybeRefOrGetter<StockFilters>) {
  return useQuery({
    queryKey: computed(() => inventoryKeys.stock(toValue(filters))),
    queryFn: () => inventoryApi.listStock(toValue(filters)),
    placeholderData: keepPreviousData,
    // Saldo é dado crítico e muda a todo momento: nunca considerado "fresco" (ADR-006).
    staleTime: 0,
  })
}

export function useMovementList(filters: MaybeRefOrGetter<MovementFilters>) {
  return useQuery({
    queryKey: computed(() => inventoryKeys.movements(toValue(filters))),
    queryFn: () => inventoryApi.listMovements(toValue(filters)),
    placeholderData: keepPreviousData,
  })
}

/**
 * Toda escrita de estoque invalida saldos, movimentações e depósitos de uma vez — inclusive em
 * erro: um 409 (ex.: STOCK_CHANGED_SINCE_COUNT) significa que a tela estava desatualizada.
 */
function useInventoryMutation<Input, Output>(mutationFn: (input: Input) => Promise<Output>) {
  const queryClient = useQueryClient()
  return useMutation({
    // Repassa só o input: o TanStack Query v5 envia um 2º argumento (contexto) que não deve
    // vazar para a camada HTTP.
    mutationFn: (input: Input) => mutationFn(input),
    onSettled: () => queryClient.invalidateQueries({ queryKey: inventoryKeys.all }),
  })
}

export const useReceiveStock = () => useInventoryMutation(inventoryApi.receiveStock)
export const useAdjustStock = () => useInventoryMutation(inventoryApi.adjustStock)
export const useTransferStock = () => useInventoryMutation(inventoryApi.transferStock)
export const useSetReorderPoint = () =>
  useInventoryMutation((input: { id: string; value: number }) =>
    inventoryApi.setReorderPoint(input.id, input.value),
  )
export const useSaveWarehouse = () =>
  useInventoryMutation((input: { id?: string; code: string; name: string }) =>
    input.id
      ? inventoryApi.renameWarehouse(input.id, input.name)
      : inventoryApi.createWarehouse({ code: input.code, name: input.name }),
  )
export const useSetWarehouseActive = () =>
  useInventoryMutation((input: { id: string; active: boolean }) =>
    inventoryApi.setWarehouseActive(input.id, input.active),
  )
