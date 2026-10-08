import { describe, expect, it } from 'vitest'

import { awaitsBackgroundWork } from '@/modules/orders/composables/useOrders'
import { buildOrder } from '@/modules/orders/tests/fixtures'
import type { Order, OrderPayment, OrderRefund } from '@/modules/orders/types'

const payment = (
  status: OrderPayment['status'],
  refunds: OrderRefund['status'][] = [],
  method: OrderPayment['method'] = 'CARD',
) => ({
  id: 'p',
  method,
  status,
  amount: '7.00',
  decline_reason: '',
  manual_reference: '',
  created_at: '2026-10-05T14:00:00Z',
  refunds: refunds.map((s, i) => ({
    id: `r${i}`,
    status: s,
    failure_reason: '',
    created_at: '2026-10-05T15:00:00Z',
  })),
})
const order = (status: Order['status'], payments: OrderPayment[]) =>
  buildOrder({ status, payments })

describe('awaitsBackgroundWork', () => {
  it.each([
    ['charge without answer', order('AWAITING_PAYMENT', [payment('PENDING')])],
    ['refund running', order('CANCELLED', [payment('APPROVED', ['PENDING'])])],
    ['approval not yet applied to the order', order('AWAITING_PAYMENT', [payment('APPROVED')])],
    [
      'refund done, order not yet refunded',
      order('CANCELLED', [payment('REFUNDED', ['SUCCEEDED'])]),
    ],
  ])('waits for %s', (_, current) => {
    expect(awaitsBackgroundWork(current)).toBe(true)
  })

  it.each([
    ['nothing paid', order('AWAITING_PAYMENT', [payment('DECLINED')])],
    ['paid', order('PAID', [payment('APPROVED')])],
    ['refunded', order('REFUNDED', [payment('REFUNDED', ['SUCCEEDED'])])],
    ['refund failed (needs a person)', order('CANCELLED', [payment('APPROVED', ['FAILED'])])],
    [
      'manual refund waits for finance',
      order('CANCELLED', [payment('APPROVED', ['PENDING'], 'MANUAL')]),
    ],
  ])('stops when %s', (_, current) => {
    expect(awaitsBackgroundWork(current)).toBe(false)
  })
})
