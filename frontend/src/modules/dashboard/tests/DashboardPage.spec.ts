import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App.vue'
import * as dashboardApi from '@/modules/dashboard/api/dashboardApi'
import type { DashboardData } from '@/modules/dashboard/types'
import { ApiError } from '@/services/http/apiError'
import { buildCurrentUser, mountWithPlugins } from '@/testing/mountWithPlugins'

vi.mock('@/modules/dashboard/api/dashboardApi')
vi.mock('@/modules/dashboard/api/healthApi', () => ({
  fetchReadiness: vi.fn(() => new Promise(() => {})),
}))

const api = vi.mocked(dashboardApi)
const manager = buildCurrentUser({ role: 'MANAGER', permissions: ['orders:read'] })

function buildData(overrides: Partial<DashboardData> = {}): DashboardData {
  return {
    period: '7d',
    start: '2026-10-01T00:00:00-03:00',
    end: '2026-10-07T15:30:00-03:00',
    bucket: 'day',
    generated_at: '2026-10-07T18:30:00+00:00',
    orders: {
      submitted: { value: 12, previous: 10 },
      series: [
        { start: '2026-10-06T00:00:00-03:00', count: 5 },
        { start: '2026-10-07T00:00:00-03:00', count: 7 },
      ],
      open_by_status: [
        { status: 'PENDING', count: 1 },
        { status: 'AWAITING_PAYMENT', count: 4 },
      ],
      recent: [
        {
          id: 'o-1',
          reference: '#000012',
          customer_name: 'Mercado Central',
          status: 'PAID',
          total: '130.00',
          submitted_at: '2026-10-07T17:00:00+00:00',
        },
      ],
    },
    money: {
      revenue: { value: '1300.00', previous: '1000.00' },
      refunded: { value: '40.00', previous: '0.00' },
      paid_orders: { value: 10, previous: 8 },
      average_ticket: { value: '134.00', previous: null },
      series: [
        { start: '2026-10-06T00:00:00-03:00', net: '500.00' },
        { start: '2026-10-07T00:00:00-03:00', net: '-40.00' },
      ],
    },
    stock: { low_stock_items: 3 },
    ...overrides,
  }
}

async function mountDashboard(route = '/dashboard') {
  const mounted = await mountWithPlugins(App, { route, user: manager })
  await flushPromises()
  return mounted
}

const tile = (wrapper: Awaited<ReturnType<typeof mountDashboard>>['wrapper'], label: string) =>
  wrapper
    .findAll('div, a')
    .find((el) => el.text().startsWith(label))
    ?.text() ?? ''

describe('DashboardPage', () => {
  beforeEach(() => vi.resetAllMocks())

  it('shows the indicators with the change against the previous period', async () => {
    api.getDashboard.mockResolvedValue(buildData())
    const { wrapper } = await mountDashboard()

    expect(api.getDashboard).toHaveBeenCalledWith('7d')
    expect(tile(wrapper, 'Pedidos recebidos')).toMatch(/12.*\+20% vs os 7 dias anteriores/s)
    expect(tile(wrapper, 'Faturamento líquido')).toMatch(/R\$\s*1\.300,00.*\+30%/s)
    expect(tile(wrapper, 'Ticket médio')).toContain('sem comparação: nada nos 7 dias anteriores')
    expect(tile(wrapper, 'Itens com estoque baixo')).toContain('3')
    const noBase = wrapper.findAll('p').find((p) => p.text().startsWith('sem comparação'))
    expect(noBase?.find('svg').classes()).toContain('text-text-secondary') // sem base: neutro
  })

  it('treats more refunds as a bad change', async () => {
    const base = buildData()
    if (!base.money) throw new Error('fixture sem dinheiro')
    api.getDashboard.mockResolvedValue(
      buildData({ money: { ...base.money, refunded: { value: '40.00', previous: '20.00' } } }),
    )
    const { wrapper } = await mountDashboard()

    const refunds = wrapper.findAll('p').find((p) => p.text().includes('+100%'))
    expect(refunds?.find('svg').classes()).toContain('text-danger') // cor só no ícone
    expect(refunds?.classes()).toContain('text-text-secondary')
  })

  it('without financial access shows orders instead of money', async () => {
    api.getDashboard.mockResolvedValue(buildData({ money: null, stock: null }))
    const { wrapper } = await mountDashboard()

    expect(wrapper.text()).not.toContain('Faturamento líquido')
    expect(wrapper.text()).not.toContain('Itens com estoque baixo')
    expect(wrapper.find('figcaption').text()).toBe('Pedidos recebidos no período')
  })

  it('switches the period through the URL', async () => {
    api.getDashboard.mockResolvedValue(buildData())
    const { wrapper, router } = await mountDashboard()

    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Hoje')
      ?.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.query.period).toBe('today')
    expect(api.getDashboard).toHaveBeenLastCalledWith('today')
  })

  it('offers the chart data as a table, in the business day', async () => {
    api.getDashboard.mockResolvedValue(buildData())
    const { wrapper } = await mountDashboard()

    const rows = wrapper.findAll('figure tbody tr').map((row) => row.text())
    expect(rows[0]).toMatch(/06\/10.*R\$\s*500,00/)
    expect(rows[1]).toMatch(/07\/10.*-R\$\s*40,00/)
  })

  it('reads a bar with the keyboard', async () => {
    api.getDashboard.mockResolvedValue(buildData())
    const { wrapper } = await mountDashboard()

    const chart = wrapper.find('figure svg')
    await chart.trigger('focus')
    await chart.trigger('keydown', { key: 'ArrowLeft' })

    expect(wrapper.find('figure [aria-live="polite"]').text()).toMatch(/06\/10: R\$\s*500,00/)
  })

  it('links the pipeline and the low stock tile to the filtered lists', async () => {
    api.getDashboard.mockResolvedValue(buildData())
    const { wrapper } = await mountDashboard()

    expect(wrapper.find('a[href="/orders?status=AWAITING_PAYMENT"]').text()).toContain('4')
    expect(wrapper.find('a[href="/stock?low=true"]').exists()).toBe(true)
  })

  it('shows the error with a retry', async () => {
    api.getDashboard.mockRejectedValue(
      new ApiError({ status: 500, code: 'UNKNOWN_ERROR', message: 'Erro' }),
    )
    const { wrapper } = await mountDashboard()

    expect(wrapper.find('[role="alert"]').text()).toContain('Tentar novamente')
  })
})
