import type {
  DraftInput,
  LineInput,
  Order,
  OrderFilters,
  OrderSummary,
  Quote,
} from '@/modules/orders/types'
import { http } from '@/services/http/client'
import type { Paginated } from '@/types/api'

export const ORDERS_PAGE_SIZE = 25

export async function listOrders(filters: OrderFilters) {
  const params: Record<string, string | number> = {
    page: filters.page,
    page_size: ORDERS_PAGE_SIZE,
  }
  if (filters.search) params.search = filters.search
  if (filters.status) params.status = filters.status
  const { data } = await http.get<Paginated<OrderSummary>>('/orders', { params })
  return data
}

export async function getOrder(id: string) {
  const { data } = await http.get<Order>(`/orders/${id}`)
  return data
}

export async function createDraft(input: DraftInput) {
  const { data } = await http.post<Order>('/orders/drafts', input)
  return data
}

export async function updateDraft(id: string, input: DraftInput) {
  const { data } = await http.patch<Order>(`/orders/${id}`, input)
  return data
}

export async function submitOrder(id: string, expectedTotal: string | null) {
  const { data } = await http.post<Order>(`/orders/${id}/submit`, { expected_total: expectedTotal })
  return data
}

/** Pedido direto (— → PENDING). Exige Idempotency-Key (ADR-012). */
export async function placeOrder(
  input: DraftInput & { expected_total: string | null },
  idempotencyKey: string,
) {
  const { data } = await http.post<Order>('/orders', input, {
    headers: { 'Idempotency-Key': idempotencyKey },
  })
  return data
}

export async function cancelOrder(id: string, reason: string) {
  const { data } = await http.post<Order>(`/orders/${id}/cancel`, { reason })
  return data
}

export async function quoteOrder(input: { customer_id: string; lines: LineInput[] }) {
  const { data } = await http.post<Quote>('/orders/quote', input)
  return data
}
