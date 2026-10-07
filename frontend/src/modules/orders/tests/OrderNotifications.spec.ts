import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App.vue'
import * as ordersApi from '@/modules/orders/api/ordersApi'
import { buildOrder } from '@/modules/orders/tests/fixtures'
import { buildCurrentUser, mountWithPlugins } from '@/testing/mountWithPlugins'

vi.mock('@/modules/orders/api/ordersApi', async (importOriginal) => ({
  ...(await importOriginal<typeof ordersApi>()),
  getOrder: vi.fn(),
  quoteOrder: vi.fn(),
  listOrderNotifications: vi.fn(),
}))

const api = vi.mocked(ordersApi)
const viewer = buildCurrentUser({ role: 'VIEWER', permissions: ['orders:read'] })
const notification = (overrides = {}) => ({
  id: 'n-1',
  kind: 'ORDER_CONFIRMED',
  status: 'SENT' as const,
  recipient: 'ma***@mercado.com',
  subject: 'Pedido #000003 confirmado — aguardando pagamento',
  attempts: 1,
  created_at: '2026-10-07T12:00:00Z',
  sent_at: '2026-10-07T12:00:05Z',
  ...overrides,
})

async function mountOrder(status: 'DRAFT' | 'PAID' = 'PAID') {
  api.getOrder.mockResolvedValue(
    buildOrder({ status, number: 3, updated_at: '2026-10-01T12:00:00Z' }),
  )
  const { wrapper } = await mountWithPlugins(App, { route: '/orders/o-1', user: viewer })
  await flushPromises()
  return wrapper
}

describe('order notifications', () => {
  beforeEach(() => vi.resetAllMocks())

  it('lists what the customer was emailed, with a masked address and status', async () => {
    api.listOrderNotifications.mockResolvedValue([
      notification(),
      notification({ id: 'n-2', kind: 'ORDER_PAID', status: 'FAILED', sent_at: null }),
    ])
    const wrapper = await mountOrder()

    const panel = wrapper.find('[aria-labelledby="order-notifications-heading"]')
    const items = panel.findAll('li').map((li) => li.text())
    expect(items[0]).toMatch(/Pedido confirmado.*Para ma\*\*\*@mercado\.com.*Enviado/s)
    expect(items[1]).toMatch(/Pagamento aprovado.*Falhou/s)
  })

  it('says when the customer had no email', async () => {
    api.listOrderNotifications.mockResolvedValue([
      notification({ status: 'SKIPPED', recipient: '', sent_at: null }),
    ])
    const wrapper = await mountOrder()

    expect(wrapper.text()).toContain('Cliente sem e-mail cadastrado')
    expect(wrapper.text()).toContain('Sem destinatário')
  })

  it('explains when nothing was sent yet', async () => {
    api.listOrderNotifications.mockResolvedValue([])
    const wrapper = await mountOrder()

    expect(wrapper.text()).toContain('Nenhum e-mail enviado ao cliente sobre este pedido ainda.')
  })

  it('is not shown for drafts (the customer never sees them)', async () => {
    api.quoteOrder.mockResolvedValue({
      lines: [],
      subtotal: '0.00',
      discount_total: '0.00',
      shipping_total: '0.00',
      total: '0.00',
      currency: 'BRL',
    })
    const wrapper = await mountOrder('DRAFT')

    expect(api.listOrderNotifications).not.toHaveBeenCalled()
    expect(wrapper.find('[aria-labelledby="order-notifications-heading"]').exists()).toBe(false)
  })
})
