import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App.vue'
import * as customersApi from '@/modules/customers/api/customersApi'
import { buildSegment } from '@/modules/customers/tests/fixtures'
import * as pricingApi from '@/modules/pricing/api/pricingApi'
import type { PriceList } from '@/modules/pricing/types'
import { buildCurrentUser, mountWithPlugins } from '@/testing/mountWithPlugins'

vi.mock('@/modules/pricing/api/pricingApi', async (importOriginal) => ({
  ...(await importOriginal<typeof pricingApi>()),
  listPriceLists: vi.fn(),
  createPriceList: vi.fn(),
}))
vi.mock('@/modules/customers/api/customersApi', async (importOriginal) => ({
  ...(await importOriginal<typeof customersApi>()),
  listSegmentOptions: vi.fn(),
}))

const api = vi.mocked(pricingApi)
const manager = buildCurrentUser({
  role: 'MANAGER',
  permissions: ['pricing:read', 'pricing:manage'],
})
const seller = buildCurrentUser({ role: 'SALES', permissions: ['pricing:read'] })

const defaultList: PriceList = {
  id: 'pl-1',
  name: 'Padrão',
  segment: null,
  is_default: true,
  currency: 'BRL',
  items_count: 12,
  created_at: '',
  updated_at: '',
}

describe('PriceListsPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.listPriceLists.mockResolvedValue([defaultList])
    vi.mocked(customersApi.listSegmentOptions).mockResolvedValue([
      buildSegment({ id: 'seg-1', name: 'Atacado' }),
      buildSegment({ id: 'seg-2', name: 'Governo', is_active: false }),
    ])
  })

  it('offers only targets that do not have a list yet', async () => {
    const { wrapper } = await mountWithPlugins(App, { route: '/price-lists', user: manager })
    await flushPromises()

    await wrapper
      .findAll('button')
      .find((b) => b.text().includes('Nova tabela'))
      ?.trigger('click')
    await flushPromises()

    const options = wrapper
      .find('#price-list-form select')
      .findAll('option')
      .map((o) => o.text())
    expect(options).toEqual(['Selecione', 'Clientes do segmento Atacado'])
  })

  it('creates a segment list and closes the dialog once the list grows', async () => {
    const created = { ...defaultList, id: 'pl-2', name: 'Atacado SP', is_default: false }
    api.createPriceList.mockResolvedValue(created)
    api.listPriceLists
      .mockResolvedValueOnce([defaultList])
      .mockResolvedValue([defaultList, created])
    const { wrapper } = await mountWithPlugins(App, { route: '/price-lists', user: manager })
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((b) => b.text().includes('Nova tabela'))
      ?.trigger('click')
    await flushPromises()

    const form = wrapper.find('#price-list-form')
    await form.find('input').setValue('Atacado SP')
    await form.find('select').setValue('seg-1')
    await form.trigger('submit')
    await flushPromises()

    expect(api.createPriceList).toHaveBeenCalledWith({ name: 'Atacado SP', segment_id: 'seg-1' })
    // Regressão: a recarga da lista não pode remontar o diálogo aberto.
    expect(wrapper.find('#price-list-form').exists()).toBe(false)
  })

  it('is read-only for sellers', async () => {
    const { wrapper } = await mountWithPlugins(App, { route: '/price-lists', user: seller })
    await flushPromises()

    expect(wrapper.text()).toContain('Tabela padrão')
    expect(wrapper.text()).not.toContain('Nova tabela')
  })
})
