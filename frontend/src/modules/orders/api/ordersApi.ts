import type {
  DraftInput,
  LineInput,
  Order,
  OrderFilters,
  OrderNotification,
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
  if (filters.ordering) params.ordering = filters.ordering
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

/** Nova tentativa de reserva de um pedido Pendente. */
export async function reserveOrder(id: string) {
  const { data } = await http.post<Order>(`/orders/${id}/reserve`)
  return data
}

/**
 * Cobrança com o token do provedor. Várias transações no backend (ADR-012): a chave identifica a
 * intenção. `accepted` = 202, o provedor não respondeu e a reconciliação vai concluir.
 */
export async function payOrder(id: string, cardToken: string, idempotencyKey: string) {
  const response = await http.post<Order>(
    `/orders/${id}/pay`,
    { card_token: cardToken },
    { headers: { 'Idempotency-Key': idempotencyKey } },
  )
  return { order: response.data, accepted: response.status === 202 }
}

/** Baixa do financeiro (boleto, PIX, transferência conciliados fora do sistema). */
export async function recordPayment(id: string, reference: string, idempotencyKey: string) {
  const { data } = await http.post<Order>(
    `/orders/${id}/record-payment`,
    { reference },
    { headers: { 'Idempotency-Key': idempotencyKey } },
  )
  return data
}

/** Separação e envio (Phase 9): idempotentes por estado, sem corpo. */
export type FulfillmentStep = 'start-picking' | 'complete-picking' | 'ship'

export async function advanceFulfillment(id: string, step: FulfillmentStep) {
  const { data } = await http.post<Order>(`/orders/${id}/${step}`)
  return data
}

export async function confirmDelivery(id: string, note: string) {
  const { data } = await http.post<Order>(`/orders/${id}/confirm-delivery`, { note })
  return data
}

export async function listOrderNotifications(id: string) {
  const { data } = await http.get<OrderNotification[]>(`/orders/${id}/notifications`)
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
