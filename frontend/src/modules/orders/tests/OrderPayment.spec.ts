import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App.vue'
import * as ordersApi from '@/modules/orders/api/ordersApi'
import { buildOrder } from '@/modules/orders/tests/fixtures'
import type { OrderPayment } from '@/modules/orders/types'
import { ApiError } from '@/services/http/apiError'
import { buildCurrentUser, mountWithPlugins } from '@/testing/mountWithPlugins'

vi.mock('@/modules/orders/api/ordersApi', async (importOriginal) => ({
  ...(await importOriginal<typeof ordersApi>()),
  getOrder: vi.fn(),
  payOrder: vi.fn(),
  recordPayment: vi.fn(),
}))

const api = vi.mocked(ordersApi)
const seller = buildCurrentUser({
  role: 'SALES',
  permissions: ['orders:read', 'orders:create', 'orders:cancel', 'payments:create'],
})
const finance = buildCurrentUser({
  role: 'FINANCE',
  permissions: ['orders:read', 'orders:cancel_paid', 'payments:read', 'payments:refund'],
})

const awaiting = buildOrder({
  status: 'AWAITING_PAYMENT',
  number: 3,
  payment_due_at: '2026-10-08T12:00:00Z',
})
const payment = (overrides: Partial<OrderPayment> = {}): OrderPayment => ({
  id: 'pay-1',
  method: 'CARD',
  status: 'APPROVED',
  amount: '7.00',
  decline_reason: '',
  manual_reference: '',
  created_at: '2026-10-05T14:00:00Z',
  refunds: [],
  ...overrides,
})
const declined = () =>
  new ApiError({
    status: 422,
    code: 'PAYMENT_DECLINED',
    message: 'Pagamento recusado pelo emissor do cartão.',
    details: { reason: 'insufficient_funds' },
  })

type Wrapper = Awaited<ReturnType<typeof mountWithPlugins>>['wrapper']
const button = (wrapper: Wrapper, text: string) => {
  const found = wrapper.findAll('button').find((b) => b.text().includes(text))
  if (!found) throw new Error(`button "${text}" not found`)
  return found
}
const keyOf = (call: number) => api.payOrder.mock.calls[call]?.[2]

async function mountOrder(user = seller) {
  const { wrapper } = await mountWithPlugins(App, { route: '/orders/o-1', user })
  await flushPromises()
  return wrapper
}

describe('order payment', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.getOrder.mockResolvedValue(awaiting)
  })

  it('pays with the chosen test card and an idempotency key', async () => {
    api.payOrder.mockResolvedValue({
      order: buildOrder({ status: 'PAID', number: 3 }),
      accepted: false,
    })
    const wrapper = await mountOrder()

    await wrapper.find('select').setValue('tok_refund_fails')
    await button(wrapper, 'com cartão').trigger('submit')
    await flushPromises()

    expect(api.payOrder).toHaveBeenCalledWith('o-1', 'tok_refund_fails', expect.any(String))
    expect(wrapper.text()).toContain('Pagamento aprovado. Pedido pago.')
  })

  it('explains that a charge without answer from the provider is still processing', async () => {
    api.payOrder.mockResolvedValue({ order: awaiting, accepted: true })
    const wrapper = await mountOrder()

    await button(wrapper, 'com cartão').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('O provedor não respondeu a tempo')
  })

  it('shows the decline and uses a new key on the next attempt', async () => {
    api.payOrder.mockRejectedValueOnce(declined()).mockRejectedValueOnce(declined())
    const wrapper = await mountOrder()

    await button(wrapper, 'com cartão').trigger('submit')
    await flushPromises()
    await button(wrapper, 'com cartão').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').text()).toContain('Pagamento recusado')
    expect(keyOf(1)).not.toBe(keyOf(0)) // a recusa foi uma resposta: nova tentativa, nova chave
  })

  it('repeats the same key after a network failure (the charge may have happened)', async () => {
    api.payOrder
      .mockRejectedValueOnce(
        new ApiError({ status: null, code: 'NETWORK_ERROR', message: 'Sem conexão' }),
      )
      .mockResolvedValueOnce({ order: buildOrder({ status: 'PAID' }), accepted: false })
    const wrapper = await mountOrder()

    await button(wrapper, 'com cartão').trigger('submit')
    await flushPromises()
    await button(wrapper, 'com cartão').trigger('submit')
    await flushPromises()

    expect(keyOf(1)).toBe(keyOf(0))
  })

  it('records a payment received outside only with a reference', async () => {
    api.recordPayment.mockResolvedValue(buildOrder({ status: 'PAID', number: 3 }))
    const wrapper = await mountOrder()

    await button(wrapper, 'Registrar pagamento recebido').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Informe a referência do pagamento.')
    expect(api.recordPayment).not.toHaveBeenCalled()

    await wrapper.find('#manual-reference input').setValue(' PIX-E2E-123 ')
    await button(wrapper, 'Registrar pagamento recebido').trigger('submit')
    await flushPromises()

    expect(api.recordPayment).toHaveBeenCalledWith('o-1', 'PIX-E2E-123', expect.any(String))
    expect(wrapper.text()).toContain('Pagamento registrado. Pedido pago.')
  })

  it('hides the payment forms while a charge is in flight', async () => {
    api.getOrder.mockResolvedValue({ ...awaiting, payments: [payment({ status: 'PENDING' })] })
    const wrapper = await mountOrder()

    expect(wrapper.text()).toContain('Pagamento em processamento: o provedor ainda não confirmou')
    expect(wrapper.text()).not.toContain('com cartão')
  })

  it('lists payments with decline reasons and refunds', async () => {
    api.getOrder.mockResolvedValue(
      buildOrder({
        status: 'CANCELLED',
        number: 3,
        payments: [
          payment({ id: 'p-1', status: 'DECLINED', decline_reason: 'insufficient_funds' }),
          payment({ id: 'p-0', status: 'DECLINED', decline_reason: 'card_expired' }),
          payment({
            id: 'p-2',
            status: 'APPROVED',
            refunds: [
              {
                id: 'r-1',
                status: 'FAILED',
                failure_reason: 'refund_rejected',
                created_at: '2026-10-05T15:00:00Z',
              },
            ],
          }),
        ],
      }),
    )
    const wrapper = await mountOrder(finance)

    const panel = wrapper.find('[aria-labelledby="order-payment-heading"]')
    expect(panel.text()).toContain('Motivo da recusa: saldo insuficiente')
    expect(panel.text()).toContain('Motivo da recusa: card_expired') // código novo: como veio
    expect(panel.text()).toContain('Estorno falhou')
    expect(panel.text()).toContain('o provedor recusou o estorno')
  })
})

describe('cancelling a paid order', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.getOrder.mockResolvedValue(buildOrder({ status: 'PAID', number: 3, payments: [payment()] }))
  })

  it('is offered with cancel_paid and warns about the refund', async () => {
    const wrapper = await mountOrder(finance)

    await button(wrapper, 'Cancelar pedido').trigger('click')

    expect(wrapper.text()).toContain('O pagamento será estornado ao cliente')
  })

  it('is not offered with the regular cancel permission only', async () => {
    const wrapper = await mountOrder(seller)

    expect(wrapper.findAll('button').some((b) => b.text().includes('Cancelar pedido'))).toBe(false)
  })
})
