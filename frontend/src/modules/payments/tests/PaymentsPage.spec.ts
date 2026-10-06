import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App.vue'
import * as paymentsApi from '@/modules/payments/api/paymentsApi'
import type { Payment } from '@/modules/payments/types'
import { ApiError } from '@/services/http/apiError'
import { buildCurrentUser, mountWithPlugins } from '@/testing/mountWithPlugins'

vi.mock('@/modules/payments/api/paymentsApi', async (importOriginal) => ({
  ...(await importOriginal<typeof paymentsApi>()),
  listPayments: vi.fn(),
  retryRefund: vi.fn(),
  confirmRefund: vi.fn(),
}))

const api = vi.mocked(paymentsApi)
const finance = buildCurrentUser({
  role: 'FINANCE',
  permissions: ['orders:read', 'payments:read', 'payments:refund'],
})
const manager = buildCurrentUser({
  role: 'MANAGER',
  permissions: ['orders:read', 'payments:read'],
})

const refund = (overrides: Partial<Payment['refunds'][number]> = {}) => ({
  id: 'r-1',
  status: 'FAILED' as const,
  amount: '7.00',
  reason: 'Cliente desistiu',
  failure_reason: 'refund_rejected',
  attempts: 1,
  created_at: '2026-10-05T15:00:00Z',
  ...overrides,
})
const payment = (overrides: Partial<Payment> = {}): Payment => ({
  id: 'p-1',
  order_id: 'o-1',
  order_reference: '#000003',
  method: 'CARD',
  status: 'APPROVED',
  amount: '7.00',
  currency: 'BRL',
  decline_reason: '',
  manual_reference: '',
  completed_at: '2026-10-05T14:00:00Z',
  created_at: '2026-10-05T14:00:00Z',
  refunds: [],
  ...overrides,
})
const page = (results: Payment[]) => ({
  count: results.length,
  next: null,
  previous: null,
  results,
})

type Wrapper = Awaited<ReturnType<typeof mountWithPlugins>>['wrapper']
const button = (wrapper: Wrapper, text: string) => {
  const found = wrapper.findAll('button').find((b) => b.text().includes(text))
  if (!found) throw new Error(`button "${text}" not found`)
  return found
}
const dialogButton = (wrapper: Wrapper, text: string) => {
  const found = wrapper
    .find('dialog')
    .findAll('button')
    .find((b) => b.text().includes(text))
  if (!found) throw new Error(`dialog button "${text}" not found`)
  return found
}
const hasButton = (wrapper: Wrapper, text: string) =>
  wrapper.findAll('button').some((b) => b.text().includes(text))

describe('PaymentsPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('lists payments with order link, method, status and amount', async () => {
    api.listPayments.mockResolvedValue(
      page([payment({ method: 'MANUAL', manual_reference: 'PIX-123' })]),
    )
    const { wrapper } = await mountWithPlugins(App, { route: '/payments', user: finance })
    await flushPromises()

    const row = wrapper.find('tbody tr')
    expect(row.find('a').attributes('href')).toBe('/orders/o-1')
    expect(row.text()).toMatch(/#000003.*Pagamento recebido.*PIX-123.*Aprovado.*R\$\s*7,00/)
  })

  it('retries a failed card refund after confirmation', async () => {
    api.listPayments.mockResolvedValue(page([payment({ refunds: [refund()] })]))
    api.retryRefund.mockResolvedValue()
    const { wrapper } = await mountWithPlugins(App, { route: '/payments', user: finance })
    await flushPromises()

    await button(wrapper, 'Tentar estorno de novo').trigger('click')
    expect(wrapper.text()).toContain('Tentar de novo o estorno do pedido #000003?')
    await dialogButton(wrapper, 'Tentar estorno de novo').trigger('click')
    await flushPromises()

    expect(api.retryRefund).toHaveBeenCalledWith('r-1', expect.any(String))
    expect(wrapper.text()).toContain('Nova tentativa de estorno enviada.')
  })

  it('keeps the dialog open with the error when the action is refused', async () => {
    api.listPayments.mockResolvedValue(
      page([payment({ method: 'MANUAL', refunds: [refund({ status: 'PENDING' })] })]),
    )
    api.confirmRefund.mockRejectedValue(
      new ApiError({ status: 409, code: 'REFUND_NOT_MANUAL', message: 'Estorno não é manual.' }),
    )
    const { wrapper } = await mountWithPlugins(App, { route: '/payments', user: finance })
    await flushPromises()

    await button(wrapper, 'Confirmar estorno feito').trigger('click')
    await dialogButton(wrapper, 'Confirmar estorno feito').trigger('click')
    await flushPromises()

    expect(wrapper.find('dialog [role="alert"]').text()).toContain('Estorno não é manual.')
  })

  it('offers refund actions only for the matching method, state and permission', async () => {
    api.listPayments.mockResolvedValue(
      page([
        payment({ id: 'a', refunds: [refund({ id: 'r-a', status: 'PENDING' })] }), // cartão em curso
        payment({ id: 'b', method: 'MANUAL', refunds: [refund({ id: 'r-b' })] }), // manual falho
      ]),
    )
    const asFinance = await mountWithPlugins(App, { route: '/payments', user: finance })
    await flushPromises()

    expect(hasButton(asFinance.wrapper, 'Tentar estorno de novo')).toBe(false)
    expect(hasButton(asFinance.wrapper, 'Confirmar estorno feito')).toBe(false)

    api.listPayments.mockResolvedValue(page([payment({ refunds: [refund()] })]))
    const asManager = await mountWithPlugins(App, { route: '/payments', user: manager })
    await flushPromises()
    expect(hasButton(asManager.wrapper, 'Tentar estorno de novo')).toBe(false)
  })

  it('filters by status through the URL', async () => {
    api.listPayments.mockResolvedValue(page([]))
    const { wrapper } = await mountWithPlugins(App, { route: '/payments', user: finance })
    await flushPromises()

    await wrapper.find('select').setValue('FAILED')
    await flushPromises()

    expect(api.listPayments).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: 'FAILED', page: 1 }),
    )
    expect(wrapper.text()).toContain('Nenhum')
  })
})
