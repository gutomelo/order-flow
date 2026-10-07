import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App.vue'
import * as ordersApi from '@/modules/orders/api/ordersApi'
import { buildOrder } from '@/modules/orders/tests/fixtures'
import type { Order, OrderHistoryEntry, OrderStatus } from '@/modules/orders/types'
import { ApiError } from '@/services/http/apiError'
import { buildCurrentUser, mountWithPlugins } from '@/testing/mountWithPlugins'

vi.mock('@/modules/orders/api/ordersApi', async (importOriginal) => ({
  ...(await importOriginal<typeof ordersApi>()),
  getOrder: vi.fn(),
  listOrders: vi.fn(),
  advanceFulfillment: vi.fn(),
  confirmDelivery: vi.fn(),
}))

const api = vi.mocked(ordersApi)
const warehouse = buildCurrentUser({
  role: 'WAREHOUSE',
  permissions: ['orders:read', 'orders:process', 'orders:ship'],
})
const seller = buildCurrentUser({
  role: 'SALES',
  permissions: ['orders:read', 'orders:create', 'orders:cancel'],
})

const PATH: OrderStatus[] = ['PAID', 'PROCESSING', 'READY_TO_SHIP', 'SHIPPED', 'DELIVERED']
function orderAt(status: OrderStatus, overrides: Partial<Order> = {}): Order {
  const history: OrderHistoryEntry[] = PATH.slice(0, PATH.indexOf(status) + 1).map((to, i) => ({
    id: `h-${i}`,
    from_status: i ? (PATH[i - 1] ?? null) : 'AWAITING_PAYMENT',
    to_status: to,
    changed_by: null,
    changed_at: '2026-10-07T12:00:00Z',
    reason: '',
  }))
  return buildOrder({
    status,
    number: 9,
    submitted_at: '2026-10-07T11:00:00Z',
    history,
    ...overrides,
  })
}
const shipment = {
  id: 's-1',
  carrier: 'Transportadora Simulada',
  tracking_code: 'SIMABC123BR',
  status: 'IN_TRANSIT' as const,
  shipped_at: '2026-10-07T13:00:00Z',
  delivered_at: null,
  delivery_source: '' as const,
  delivery_note: '',
}

type Wrapper = Awaited<ReturnType<typeof mountWithPlugins>>['wrapper']
const button = (scope: Pick<Wrapper, 'findAll'>, text: string) => {
  const found = scope.findAll('button').find((b) => b.text().includes(text))
  if (!found) throw new Error(`button "${text}" not found`)
  return found
}
const hasButton = (wrapper: Wrapper, text: string) =>
  wrapper.findAll('button').some((b) => b.text().includes(text))

async function mountOrder(order: Order, user = warehouse) {
  api.getOrder.mockResolvedValue(order)
  const { wrapper } = await mountWithPlugins(App, { route: '/orders/o-1', user })
  await flushPromises()
  return wrapper
}

describe('order fulfillment', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('starts picking a paid order in one click', async () => {
    api.advanceFulfillment.mockResolvedValue(orderAt('PROCESSING'))
    const wrapper = await mountOrder(orderAt('PAID'))

    await button(wrapper, 'Iniciar separação').trigger('click')
    await flushPromises()

    expect(api.advanceFulfillment).toHaveBeenCalledWith('o-1', 'start-picking')
    expect(wrapper.text()).toContain('Separação do pedido #000009 iniciada.')
  })

  it('asks for confirmation before shipping and keeps the dialog open on error', async () => {
    api.advanceFulfillment.mockRejectedValue(
      new ApiError({
        status: 503,
        code: 'SHIPPING_PROVIDER_UNAVAILABLE',
        message: 'A transportadora não respondeu. Tente despachar de novo em instantes.',
      }),
    )
    const wrapper = await mountOrder(orderAt('READY_TO_SHIP'))

    await button(wrapper, 'Despachar').trigger('click')
    expect(api.advanceFulfillment).not.toHaveBeenCalled()
    const dialog = wrapper.find('dialog')
    expect(dialog.text()).toContain('Despachar o pedido #000009?')
    expect(dialog.text()).toContain('não pode mais ser cancelado')
    await button(dialog, 'Despachar').trigger('click')
    await flushPromises()

    expect(api.advanceFulfillment).toHaveBeenCalledWith('o-1', 'ship')
    expect(wrapper.find('dialog [role="alert"]').text()).toContain('A transportadora não respondeu')
  })

  it('shows the shipment and confirms a delivery by hand with a note', async () => {
    api.confirmDelivery.mockResolvedValue(orderAt('DELIVERED'))
    const wrapper = await mountOrder(orderAt('SHIPPED', { shipment }))

    const panel = wrapper.find('[aria-labelledby="order-fulfillment-heading"]')
    expect(panel.text()).toContain('Transportadora Simulada')
    expect(panel.text()).toContain('SIMABC123BR')
    expect(panel.text()).toContain('Em trânsito')
    await button(wrapper, 'Confirmar entrega').trigger('click')
    await wrapper.find('dialog textarea').setValue('  Recebido por Maria ')
    await wrapper.find('dialog form').trigger('submit')
    await flushPromises()

    expect(api.confirmDelivery).toHaveBeenCalledWith('o-1', 'Recebido por Maria')
    expect(wrapper.text()).toContain('Entrega do pedido #000009 confirmada.')
  })

  it('tells how a delivery was confirmed', async () => {
    const wrapper = await mountOrder(
      orderAt('DELIVERED', {
        shipment: {
          ...shipment,
          status: 'DELIVERED',
          delivered_at: '2026-10-08T10:00:00Z',
          delivery_source: 'PROVIDER',
        },
      }),
    )

    const panel = wrapper.find('[aria-labelledby="order-fulfillment-heading"]')
    expect(panel.text()).toContain('Confirmada pelo rastreio da transportadora')
    expect(panel.findAll('li').map((li) => li.text())).toEqual([
      'Separação iniciada (concluída)',
      'Separado e embalado (concluída)',
      'Despachado (concluída)',
      'Entregue (concluída)',
    ])
    expect(hasButton(wrapper, 'Confirmar entrega')).toBe(false)
  })

  it('offers no fulfillment action without the logistics permissions', async () => {
    const wrapper = await mountOrder(orderAt('PAID'), seller)

    expect(wrapper.find('[aria-labelledby="order-fulfillment-heading"]').exists()).toBe(true)
    expect(hasButton(wrapper, 'Iniciar separação')).toBe(false)
  })
})

describe('FulfillmentPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  const page = (results: Order[]) => ({
    count: results.length,
    next: null,
    previous: null,
    results,
  })

  it('lists the queue of a step, oldest first, with the next action on each row', async () => {
    api.listOrders.mockResolvedValue(page([orderAt('PAID')]))
    const { wrapper } = await mountWithPlugins(App, { route: '/fulfillment', user: warehouse })
    await flushPromises()

    expect(api.listOrders).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: 'PAID', ordering: 'submitted_at', page: 1 }),
    )
    const row = wrapper.find('tbody tr')
    expect(row.text()).toContain('#000009')
    expect(row.text()).toContain('Iniciar separação')

    await button(wrapper, 'Prontos para envio').trigger('click')
    await flushPromises()
    expect(api.listOrders).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: 'READY_TO_SHIP' }),
    )
    expect(button(wrapper, 'Prontos para envio').attributes('aria-pressed')).toBe('true')
  })

  it('explains an empty step', async () => {
    api.listOrders.mockResolvedValue(page([]))
    const { wrapper } = await mountWithPlugins(App, {
      route: '/fulfillment?status=SHIPPED',
      user: warehouse,
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Nenhum pedido em trânsito.')
  })

  it('is not reachable without orders:process', async () => {
    const { wrapper } = await mountWithPlugins(App, { route: '/fulfillment', user: seller })
    await flushPromises()

    expect(api.listOrders).not.toHaveBeenCalled()
    expect(wrapper.text()).not.toContain('Pedidos pagos a separar')
  })
})
