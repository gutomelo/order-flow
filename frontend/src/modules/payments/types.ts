import type { OrderRefund, PaymentStatus } from '@/modules/orders/types'

export interface Payment {
  id: string
  order_id: string
  order_reference: string
  method: 'CARD' | 'MANUAL'
  status: PaymentStatus
  amount: string
  currency: string
  decline_reason: string
  manual_reference: string
  completed_at: string | null
  created_at: string
  refunds: (OrderRefund & { amount: string; reason: string; attempts: number })[]
}

export interface PaymentFilters {
  page: number
  search: string
  status: PaymentStatus | ''
}
