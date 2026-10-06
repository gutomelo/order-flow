import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'

import { inventoryKeys } from '@/modules/inventory/composables/useInventory'
import * as api from '@/modules/orders/api/ordersApi'
import type { DraftInput, LineInput, Order, OrderFilters } from '@/modules/orders/types'

export const ordersKeys = {
  all: ['orders'] as const,
  list: (filters: OrderFilters) => [...ordersKeys.all, 'list', filters] as const,
  detail: (id: string) => [...ordersKeys.all, 'detail', id] as const,
  quote: (input: { customer_id: string; lines: LineInput[] }) =>
    [...ordersKeys.all, 'quote', input] as const,
}

export function useOrdersList(filters: MaybeRefOrGetter<OrderFilters>) {
  return useQuery({
    queryKey: computed(() => ordersKeys.list(toValue(filters))),
    queryFn: () => api.listOrders(toValue(filters)),
    placeholderData: keepPreviousData,
  })
}

const PENDING_POLL_MS = 5000

/**
 * Há trabalho do backend em curso: cobrança sem resposta (reconciliação), estorno em execução, ou
 * resultado já gravado em `payments` que o pedido só aplica quando o evento chega (outbox, ADR-011).
 */
export function awaitsBackgroundWork(order: Order | undefined): boolean {
  if (!order) return false
  const payments = order.payments
  const refunds = payments.flatMap((p) => p.refunds)
  return (
    payments.some((p) => p.status === 'PENDING') ||
    // Estorno manual pendente espera o financeiro, não o backend.
    payments.some((p) => p.method === 'CARD' && p.refunds.some((r) => r.status === 'PENDING')) ||
    (['PENDING', 'AWAITING_PAYMENT'].includes(order.status) &&
      payments.some((p) => p.status === 'APPROVED')) ||
    (order.status === 'CANCELLED' && refunds.some((r) => r.status === 'SUCCEEDED'))
  )
}

export function useOrder(id: MaybeRefOrGetter<string | undefined>) {
  return useQuery({
    queryKey: computed(() => ordersKeys.detail(toValue(id) ?? '')),
    queryFn: () => api.getOrder(toValue(id) ?? ''),
    enabled: computed(() => Boolean(toValue(id))),
    // Enquanto o backend conclui algo em background, a tela acompanha sem a pessoa recarregar.
    refetchInterval: (query) => (awaitsBackgroundWork(query.state.data) ? PENDING_POLL_MS : false),
  })
}

/** Prévia calculada pelo backend: o frontend não soma dinheiro. */
export function useQuote(
  input: MaybeRefOrGetter<{ customer_id: string; lines: LineInput[] } | null>,
) {
  return useQuery({
    queryKey: computed(() => ordersKeys.quote(toValue(input) ?? { customer_id: '', lines: [] })),
    queryFn: () => {
      const value = toValue(input)
      if (!value) throw new Error('quote without input')
      return api.quoteOrder(value)
    },
    enabled: computed(() => Boolean(toValue(input)?.lines.length)),
    placeholderData: keepPreviousData,
    staleTime: 0,
  })
}

/**
 * Invalida `orders` e o estoque ao terminar — inclusive no erro (409 = tela desatualizada).
 * Enviar, reservar e cancelar mudam o disponível (reservas), então o estoque também recarrega.
 */
function useOrdersMutation<Input, Output>(mutationFn: (input: Input) => Promise<Output>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: Input) => mutationFn(input),
    onSettled: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ordersKeys.all }),
        queryClient.invalidateQueries({ queryKey: inventoryKeys.all }),
      ]),
  })
}

export const useSaveDraft = () =>
  useOrdersMutation((input: { id?: string; data: DraftInput }) =>
    input.id ? api.updateDraft(input.id, input.data) : api.createDraft(input.data),
  )

export const useSubmitOrder = () =>
  useOrdersMutation((input: { id: string; expectedTotal: string | null }) =>
    api.submitOrder(input.id, input.expectedTotal),
  )

export const usePlaceOrder = () =>
  useOrdersMutation(
    (input: { data: DraftInput & { expected_total: string | null }; key: string }) =>
      api.placeOrder(input.data, input.key),
  )

export const usePayOrder = () =>
  useOrdersMutation((input: { id: string; cardToken: string; key: string }) =>
    api.payOrder(input.id, input.cardToken, input.key),
  )

export const useRecordPayment = () =>
  useOrdersMutation((input: { id: string; reference: string; key: string }) =>
    api.recordPayment(input.id, input.reference, input.key),
  )

export const useReserveOrder = () => useOrdersMutation((id: string) => api.reserveOrder(id))

export const useCancelOrder = () =>
  useOrdersMutation((input: { id: string; reason: string }) =>
    api.cancelOrder(input.id, input.reason),
  )
