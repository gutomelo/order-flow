import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'

import { ordersKeys } from '@/modules/orders/composables/useOrders'
import * as api from '@/modules/payments/api/paymentsApi'
import type { PaymentFilters } from '@/modules/payments/types'

const PENDING_POLL_MS = 5000

export const paymentsKeys = {
  all: ['payments'] as const,
  list: (filters: PaymentFilters) => [...paymentsKeys.all, 'list', filters] as const,
}

export function usePaymentsList(filters: MaybeRefOrGetter<PaymentFilters>) {
  return useQuery({
    queryKey: computed(() => paymentsKeys.list(toValue(filters))),
    queryFn: () => api.listPayments(toValue(filters)),
    placeholderData: keepPreviousData,
    // Cobranças em reconciliação e estornos no provedor terminam em background.
    refetchInterval: (query) =>
      query.state.data?.results.some(
        (p) =>
          p.status === 'PENDING' ||
          (p.method === 'CARD' && p.refunds.some((r) => r.status === 'PENDING')),
      )
        ? PENDING_POLL_MS
        : false,
  })
}

/** Ações de estorno mudam pagamentos e o status do pedido (CANCELLED → REFUNDED). */
function usePaymentsMutation<Input>(mutationFn: (input: Input) => Promise<void>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: Input) => mutationFn(input),
    onSettled: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: paymentsKeys.all }),
        queryClient.invalidateQueries({ queryKey: ordersKeys.all }),
      ]),
  })
}

export const useRetryRefund = () =>
  usePaymentsMutation((input: { id: string; key: string }) => api.retryRefund(input.id, input.key))

export const useConfirmRefund = () =>
  usePaymentsMutation((input: { id: string; key: string }) =>
    api.confirmRefund(input.id, input.key),
  )
