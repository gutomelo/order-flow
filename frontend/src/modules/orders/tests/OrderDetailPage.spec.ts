import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App.vue'
import * as inventoryApi from '@/modules/inventory/api/inventoryApi'
import * as ordersApi from '@/modules/orders/api/ordersApi'
import { buildOrder, buildQuote } from '@/modules/orders/tests/fixtures'
import { ApiError } from '@/services/http/apiError'
import { buildCurrentUser, mountWithPlugins } from '@/testing/mountWithPlugins'

vi.mock('@/modules/orders/api/ordersApi', async (importOriginal) => ({
  ...(await importOriginal<typeof ordersApi>()),
  getOrder: vi.fn(),
  submitOrder: vi.fn(),
  cancelOrder: vi.fn(),
  quoteOrder: vi.fn(),
  reserveOrder: vi.fn(),
}))
vi.mock('@/modules/inventory/api/inventoryApi', async (importOriginal) => ({
  ...(await importOriginal<typeof inventoryApi>()),
  getAvailability: vi.fn(),
}))

const api = vi.mocked(ordersApi)
const seller = buildCurrentUser({
  role: 'SALES',
  permissions: ['orders:read', 'orders:create', 'orders:cancel', 'inventory:read'],
})
const viewer = buildCurrentUser({ role: 'VIEWER', permissions: ['orders:read'] })

const button = (wrapper: Awaited<ReturnType<typeof mountWithPlugins>>['wrapper'], text: string) => {
  const found = wrapper.findAll('button').find((b) => b.text().includes(text))
  if (!found) throw new Error(`button "${text}" not found`)
  return found
}

describe('OrderDetailPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.getOrder.mockResolvedValue(buildOrder())
    api.quoteOrder.mockResolvedValue(buildQuote())
  })

  it('shows the current price of a draft and submits the total on screen', async () => {
    // Rascunho salvo a R$ 3,50; a tabela agora diz R$ 3,90.
    api.quoteOrder.mockResolvedValue(
      buildQuote({
        lines: buildQuote().lines.map((line) => ({
          ...line,
          unit_price: '3.90',
          line_total: '7.80',
        })),
        subtotal: '7.80',
        total: '7.80',
      }),
    )
    api.submitOrder.mockResolvedValue(buildOrder({ status: 'PENDING', number: 1 }))
    const { wrapper } = await mountWithPlugins(App, { route: '/orders/o-1', user: seller })
    await flushPromises()

    expect(wrapper.find('tbody').text()).toMatch(/R\$\s*3,90.*R\$\s*7,80/)
    await button(wrapper, 'Enviar pedido').trigger('click')
    await flushPromises()

    expect(api.submitOrder).toHaveBeenCalledWith('o-1', '7.80')
  })

  it('shows a submitted order with number, status, frozen lines and history', async () => {
    api.getOrder.mockResolvedValue(
      buildOrder({ status: 'PENDING', number: 42, submitted_at: '2026-10-05T13:00:00Z' }),
    )
    const { wrapper } = await mountWithPlugins(App, { route: '/orders/o-1', user: seller })
    await flushPromises()

    expect(wrapper.find('h1').text()).toBe('#000042')
    expect(wrapper.text()).toContain('Pendente')
    expect(wrapper.find('tbody').text()).toMatch(
      /COLA.*Refrigerante Cola.*2.*R\$\s*3,50.*R\$\s*7,00/,
    )
    expect(wrapper.text()).toContain('Criado como Rascunho')
    expect(wrapper.text()).not.toContain('Enviar pedido')
  })

  it('asks for confirmation of the new total when prices changed since the draft was saved', async () => {
    api.submitOrder.mockRejectedValueOnce(
      new ApiError({
        status: 409,
        code: 'PRICES_CHANGED',
        message: 'Os preços mudaram.',
        details: { expected: '7.00', actual: '8.00' },
      }),
    )
    api.submitOrder.mockResolvedValueOnce(buildOrder({ status: 'PENDING', number: 1 }))
    const { wrapper } = await mountWithPlugins(App, { route: '/orders/o-1', user: seller })
    await flushPromises()

    await button(wrapper, 'Enviar pedido').trigger('click')
    await flushPromises()
    expect(api.submitOrder).toHaveBeenLastCalledWith('o-1', '7.00')
    expect(wrapper.find('[role="alert"]').text()).toMatch(/novo total é R\$\s*8,00/)

    await button(wrapper, 'Enviar com o novo total').trigger('click')
    await flushPromises()

    expect(api.submitOrder).toHaveBeenLastCalledWith('o-1', '8.00')
    // Mock devolve PENDING: enviado, mas sem estoque para reservar.
    expect(wrapper.text()).toContain('Pedido #000001 enviado, mas ficou pendente')
  })

  it('requires a reason to cancel', async () => {
    api.getOrder.mockResolvedValue(buildOrder({ status: 'PENDING', number: 7 }))
    api.cancelOrder.mockResolvedValue(buildOrder({ status: 'CANCELLED', number: 7 }))
    const { wrapper } = await mountWithPlugins(App, { route: '/orders/o-1', user: seller })
    await flushPromises()

    await button(wrapper, 'Cancelar pedido').trigger('click')
    const form = wrapper.find('#cancel-order-form')
    await form.trigger('submit')
    await flushPromises()
    expect(form.text()).toContain('Informe o motivo do cancelamento.')
    expect(api.cancelOrder).not.toHaveBeenCalled()

    await form.find('textarea').setValue('Cliente desistiu')
    await form.trigger('submit')
    await flushPromises()

    expect(api.cancelOrder).toHaveBeenCalledWith('o-1', 'Cliente desistiu')
  })

  it('shows no actions to read-only roles', async () => {
    const { wrapper } = await mountWithPlugins(App, { route: '/orders/o-1', user: viewer })
    await flushPromises()

    const labels = wrapper.findAll('main button, main a').map((el) => el.text())
    expect(labels.some((l) => /Enviar|Editar|Cancelar|Descartar/.test(l))).toBe(false)
  })

  it('explains a missing reservation, shows what is short and lists each shortage on retry', async () => {
    api.getOrder.mockResolvedValue(buildOrder({ status: 'PENDING', number: 3 }))
    vi.mocked(inventoryApi.getAvailability).mockResolvedValue([
      { product_id: 'p-cola', on_hand: 1, reserved: 0, available: 1 },
    ])
    api.reserveOrder.mockRejectedValue(
      new ApiError({
        status: 409,
        code: 'INSUFFICIENT_STOCK',
        message: 'Estoque insuficiente.',
        details: { lines: [{ product_id: 'p-cola', requested: 2, available: 1 }] },
      }),
    )
    const { wrapper } = await mountWithPlugins(App, { route: '/orders/o-1', user: seller })
    await flushPromises()

    const panel = wrapper.find('section[aria-labelledby="reservation-heading"]')
    expect(panel.text()).toContain('Sem reserva de estoque')
    expect(wrapper.find('tbody').text()).toContain('Faltam 1')

    await button(wrapper, 'Reservar estoque').trigger('click')
    await flushPromises()

    expect(api.reserveOrder).toHaveBeenCalledWith('o-1')
    expect(panel.text()).toContain('COLA: pedido 2, disponível 1')
  })

  it('confirms a successful reservation with its expiry', async () => {
    api.getOrder.mockResolvedValue(buildOrder({ status: 'PENDING', number: 3 }))
    vi.mocked(inventoryApi.getAvailability).mockResolvedValue([])
    api.reserveOrder.mockResolvedValue(
      buildOrder({
        status: 'AWAITING_PAYMENT',
        number: 3,
        payment_due_at: '2026-10-08T12:00:00Z',
      }),
    )
    const { wrapper } = await mountWithPlugins(App, { route: '/orders/o-1', user: seller })
    await flushPromises()

    await button(wrapper, 'Reservar estoque').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toMatch(/Estoque reservado até 0?8\/10\/2026/)
  })

  it('tells that cancelling a reserved order gives the stock back', async () => {
    api.getOrder.mockResolvedValue(
      buildOrder({ status: 'AWAITING_PAYMENT', number: 3, payment_due_at: '2026-10-08T12:00:00Z' }),
    )
    const { wrapper } = await mountWithPlugins(App, { route: '/orders/o-1', user: seller })
    await flushPromises()

    expect(wrapper.text()).toMatch(/Estoque reservado até 0?8\/10\/2026/)
    await button(wrapper, 'Cancelar pedido').trigger('click')

    expect(wrapper.text()).toContain('O estoque reservado volta a ficar disponível')
  })
})
