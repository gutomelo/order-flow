import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App.vue'
import * as auditApi from '@/modules/audit/api/auditApi'
import type { AuditLog } from '@/modules/audit/types'
import { buildCurrentUser, mountWithPlugins } from '@/testing/mountWithPlugins'

vi.mock('@/modules/audit/api/auditApi', async (importOriginal) => ({
  ...(await importOriginal<typeof auditApi>()),
  listAuditLogs: vi.fn(),
}))

const api = vi.mocked(auditApi)
const manager = buildCurrentUser({ role: 'MANAGER', permissions: ['audit:read'] })
const seller = buildCurrentUser({ role: 'SALES', permissions: ['orders:read'] })

function buildLog(overrides: Partial<AuditLog> = {}): AuditLog {
  return {
    id: 'a-1',
    action: 'ORDER_CANCELLED',
    entity_type: 'ORDER',
    entity_id: 'o-1',
    entity_label: '#000003',
    order_id: 'o-1',
    actor: { id: 'u-1', name: 'Ana Souza' },
    reason: 'Cliente desistiu',
    changes: { status: ['PAID', 'CANCELLED'] },
    occurred_at: '2026-10-08T13:00:00Z',
    request_id: 'req-1',
    ...overrides,
  }
}
const page = (results: AuditLog[]) => ({
  count: results.length,
  next: null,
  previous: null,
  results,
})

describe('AuditPage', () => {
  beforeEach(() => vi.resetAllMocks())

  it('shows who did what, on which item, with the before and after', async () => {
    api.listAuditLogs.mockResolvedValue(
      page([
        buildLog(),
        buildLog({
          id: 'a-2',
          action: 'PAYMENT_APPROVED',
          entity_type: 'PAYMENT',
          actor: null,
          reason: '',
          changes: { amount: '13.00', method: 'CARD', status: ['PENDING', 'APPROVED'] }, // ordem do jsonb
        }),
        buildLog({
          id: 'a-3',
          action: 'STOCK_ADJUSTED',
          entity_type: 'STOCK_ITEM',
          entity_label: 'COLA · CD-SP',
          order_id: null,
          reason: 'Quebra',
          changes: { on_hand: [10, 7] },
        }),
      ]),
    )
    const { wrapper } = await mountWithPlugins(App, { route: '/audit', user: manager })
    await flushPromises()

    const rows = wrapper.findAll('tbody tr').map((row) => row.text())
    expect(rows[0]).toMatch(
      /Ana Souza.*Pedido cancelado.*#000003.*Status: Pago → Cancelado.*Cliente desistiu/s,
    )
    expect(rows[1]).toMatch(
      /Sistema.*Pagamento aprovado.*Status: Em processamento → Aprovado.*Valor: R\$\s*13,00.*Forma: Cartão/s,
    )
    expect(rows[2]).toMatch(/Ajuste de estoque.*COLA · CD-SP.*Saldo físico: 10 → 7/s)
    expect(wrapper.find('tbody a[href="/orders/o-1"]').exists()).toBe(true)
  })

  it('filters by action and period through the URL', async () => {
    api.listAuditLogs.mockResolvedValue(page([]))
    const { wrapper, router } = await mountWithPlugins(App, {
      route: '/audit?from=2026-10-01',
      user: manager,
    })
    await flushPromises()

    await wrapper.findAll('select')[0]?.setValue('STOCK_ADJUSTED')
    await flushPromises()

    expect(router.currentRoute.value.query.action).toBe('STOCK_ADJUSTED')
    expect(api.listAuditLogs).toHaveBeenLastCalledWith(
      expect.objectContaining({ action: 'STOCK_ADJUSTED', from: '2026-10-01', page: 1 }),
    )
    expect(wrapper.text()).toContain('Nenhum')
  })

  it('is not reachable without audit:read', async () => {
    const { wrapper } = await mountWithPlugins(App, { route: '/audit', user: seller })
    await flushPromises()

    expect(api.listAuditLogs).not.toHaveBeenCalled()
    expect(wrapper.text()).not.toContain('Quem fez o quê')
  })
})

describe('listAuditLogs', () => {
  it('sends the chosen days as UTC bounds in the viewer time zone', async () => {
    const { http } = await import('@/services/http/client')
    const spy = vi.spyOn(http, 'get').mockResolvedValue({ data: page([]) })
    const real = await vi.importActual<typeof auditApi>('@/modules/audit/api/auditApi')

    await real.listAuditLogs({
      page: 1,
      search: '',
      action: '',
      entity_type: '',
      from: '2026-10-01',
      to: '2026-10-01',
    })

    const params = (spy.mock.calls[0]?.[1] as { params: Record<string, string> }).params
    const start = new Date(params.occurred_after ?? '')
    const end = new Date(params.occurred_before ?? '')
    expect(end.getTime() - start.getTime()).toBe(24 * 60 * 60 * 1000)
    expect(start.getDate()).toBe(1)
    spy.mockRestore()
  })
})
