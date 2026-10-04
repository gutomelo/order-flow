import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App.vue'
import * as inventoryApi from '@/modules/inventory/api/inventoryApi'
import type { StockItem } from '@/modules/inventory/types'
import { ApiError } from '@/services/http/apiError'
import { buildCurrentUser, mountWithPlugins } from '@/testing/mountWithPlugins'

vi.mock('@/modules/inventory/api/inventoryApi', async (importOriginal) => ({
  ...(await importOriginal<typeof inventoryApi>()),
  listStock: vi.fn(),
  listWarehouses: vi.fn(),
  adjustStock: vi.fn(),
  getStockItem: vi.fn(),
}))

const api = vi.mocked(inventoryApi)

const operator = buildCurrentUser({
  role: 'WAREHOUSE',
  permissions: ['inventory:read', 'inventory:update', 'inventory:adjust'],
})
const viewer = buildCurrentUser({ role: 'VIEWER', permissions: ['inventory:read'] })

function buildItem(overrides: Partial<StockItem> = {}): StockItem {
  return {
    id: 'si-1',
    product: { id: 'p-1', sku: 'CAFE-500', name: 'Café 500g', is_active: true },
    warehouse: { id: 'w-1', code: 'CD-SP', name: 'CD São Paulo' },
    on_hand: 10,
    reserved: 6,
    available: 4,
    reorder_point: 5,
    is_low_stock: true,
    updated_at: '2026-10-04T12:00:00Z',
    ...overrides,
  }
}

const page = (results: StockItem[]) => ({
  count: results.length,
  next: null,
  previous: null,
  results,
})

async function openAdjust() {
  const mounted = await mountWithPlugins(App, { route: '/stock', user: operator })
  await flushPromises()
  await mounted.wrapper
    .findAll('tbody button')
    .find((button) => button.text().includes('Ajustar CAFE-500'))
    ?.trigger('click')
  await flushPromises()
  return mounted
}

// A página tem mais de um <dialog> (recebimento, ajuste...): mira o que contém o formulário.
const adjustDialog = (wrapper: Awaited<ReturnType<typeof mountWithPlugins>>['wrapper']) => {
  const dialog = wrapper
    .findAll('dialog')
    .find((candidate) => candidate.find('#adjust-form').exists())
  if (!dialog) throw new Error('adjust dialog not found')
  return dialog
}

describe('StockPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.listWarehouses.mockResolvedValue([])
    api.listStock.mockResolvedValue(page([buildItem()]))
  })

  it('shows physical, reserved and available balances with a textual low-stock status', async () => {
    const { wrapper } = await mountWithPlugins(App, { route: '/stock', user: operator })
    await flushPromises()

    const row = wrapper.find('tbody tr').text()
    expect(row).toContain('Café 500g')
    expect(row).toContain('CD-SP')
    expect(row).toMatch(/10\s*6\s*4/)
    expect(row).toContain('Abaixo do mínimo (5)')
  })

  it('hides stock operations from read-only roles', async () => {
    const { wrapper } = await mountWithPlugins(App, { route: '/stock', user: viewer })
    await flushPromises()

    expect(wrapper.text()).not.toContain('Receber mercadoria')
    const actions = wrapper.findAll('tbody button').map((button) => button.text())
    expect(actions.some((label) => label.includes('Ajustar'))).toBe(false)
    // O histórico continua acessível para leitura.
    expect(wrapper.find('tbody a[href*="/movements"]').exists()).toBe(true)
  })

  it('sends the balance seen on screen as expected_on_hand and previews the difference', async () => {
    api.adjustStock.mockResolvedValue(buildItem({ on_hand: 7, available: 1 }))
    const { wrapper } = await openAdjust()

    const inputs = wrapper.findAll('dialog input')
    await inputs[0]?.setValue('7')
    expect(adjustDialog(wrapper).text()).toContain('-3')
    await wrapper.find('dialog textarea').setValue('Inventário mensal')
    await wrapper.find('#adjust-form').trigger('submit')
    await flushPromises()

    expect(api.adjustStock).toHaveBeenCalledWith({
      stock_item_id: 'si-1',
      counted_quantity: 7,
      expected_on_hand: 10,
      reason: 'Inventário mensal',
    })
    expect(wrapper.text()).toContain('Ajuste registrado.')
  })

  it('shows the new balance after a concurrent change and resubmits against it', async () => {
    api.adjustStock.mockRejectedValueOnce(
      new ApiError({
        status: 409,
        code: 'STOCK_CHANGED_SINCE_COUNT',
        message: 'O saldo mudou desde a contagem. Atualize a tela e conte novamente.',
      }),
    )
    api.getStockItem.mockResolvedValue(buildItem({ on_hand: 12, available: 6 }))
    const { wrapper } = await openAdjust()

    await wrapper.findAll('dialog input')[0]?.setValue('7')
    await wrapper.find('dialog textarea').setValue('Inventário mensal')
    await wrapper.find('#adjust-form').trigger('submit')
    await flushPromises()

    const dialog = adjustDialog(wrapper)
    expect(dialog.find('[role="alert"]').text()).toContain('mudou de 10 para 12')
    expect(dialog.text()).toContain('-5')

    api.adjustStock.mockResolvedValueOnce(buildItem({ on_hand: 7, available: 1 }))
    await wrapper.find('#adjust-form').trigger('submit')
    await flushPromises()

    expect(api.adjustStock).toHaveBeenLastCalledWith(
      expect.objectContaining({ counted_quantity: 7, expected_on_hand: 12 }),
    )
    expect(wrapper.text()).toContain('Ajuste registrado.')
  })

  it('requires a reason for adjustments', async () => {
    const { wrapper } = await openAdjust()

    await wrapper.findAll('dialog input')[0]?.setValue('7')
    await wrapper.find('#adjust-form').trigger('submit')
    await flushPromises()

    expect(adjustDialog(wrapper).text()).toContain('Descreva o motivo')
    expect(api.adjustStock).not.toHaveBeenCalled()
  })
})
