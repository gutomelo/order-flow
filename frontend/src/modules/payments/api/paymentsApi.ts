import type { Payment, PaymentFilters } from '@/modules/payments/types'
import { http } from '@/services/http/client'
import type { Paginated } from '@/types/api'

export const PAYMENTS_PAGE_SIZE = 25

export async function listPayments(filters: PaymentFilters) {
  const params: Record<string, string | number> = {
    page: filters.page,
    page_size: PAYMENTS_PAGE_SIZE,
  }
  if (filters.search) params.search = filters.search
  if (filters.status) params.status = filters.status
  const { data } = await http.get<Paginated<Payment>>('/payments', { params })
  return data
}

export async function retryRefund(id: string, idempotencyKey: string) {
  await http.post(`/refunds/${id}/retry`, null, { headers: { 'Idempotency-Key': idempotencyKey } })
}

export async function confirmRefund(id: string, idempotencyKey: string) {
  await http.post(`/refunds/${id}/confirm`, null, {
    headers: { 'Idempotency-Key': idempotencyKey },
  })
}
