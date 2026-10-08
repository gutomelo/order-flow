import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App.vue'
import * as customersApi from '@/modules/customers/api/customersApi'
import { buildCustomer, buildSegment, page } from '@/modules/customers/tests/fixtures'
import { ApiError } from '@/services/http/apiError'
import { buildCurrentUser, mountWithPlugins } from '@/testing/mountWithPlugins'

vi.mock('@/modules/customers/api/customersApi', async (importOriginal) => ({
  ...(await importOriginal<typeof customersApi>()),
  listCustomers: vi.fn(),
  listSegmentOptions: vi.fn(),
  createCustomer: vi.fn(),
  getCustomer: vi.fn(),
  listAddresses: vi.fn(),
  listContacts: vi.fn(),
}))

const api = vi.mocked(customersApi)
const seller = buildCurrentUser({
  role: 'SALES',
  permissions: ['customers:read', 'customers:create', 'customers:update'],
})
const viewer = buildCurrentUser({ role: 'VIEWER', permissions: ['customers:read'] })

describe('CustomersPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.listCustomers.mockResolvedValue(page([buildCustomer()]))
    api.listSegmentOptions.mockResolvedValue([
      buildSegment(),
      buildSegment({ id: 'seg-2', name: 'Governo', is_active: false }),
    ])
  })

  it('lists customers with segment and a link to the detail page', async () => {
    const { wrapper } = await mountWithPlugins(App, { route: '/customers', user: seller })
    await flushPromises()

    const row = wrapper.find('tbody tr')
    expect(row.text()).toContain('11.222.333/0001-81')
    expect(row.text()).toContain('Atacado')
    expect(row.find('a').attributes('href')).toBe('/customers/c-1')
  })

  it('filters by segment through the URL', async () => {
    const { wrapper, router } = await mountWithPlugins(App, {
      route: '/customers',
      user: seller,
    })
    await flushPromises()

    const segmentSelect = wrapper
      .findAll('select')
      .find((select) => select.text().includes('Todos os segmentos'))
    expect(segmentSelect?.text()).toContain('Governo (inativo)')
    await segmentSelect?.setValue('seg-1')
    await flushPromises()

    expect(router.currentRoute.value.query.segment).toBe('seg-1')
    expect(api.listCustomers).toHaveBeenLastCalledWith(
      expect.objectContaining({ segment: 'seg-1', page: 1 }),
    )
  })

  it('hides creation from read-only roles', async () => {
    const { wrapper } = await mountWithPlugins(App, { route: '/customers', user: viewer })
    await flushPromises()

    expect(wrapper.text()).not.toContain('Novo cliente')
  })

  it('creates a customer and opens its detail page', async () => {
    api.createCustomer.mockResolvedValue(buildCustomer({ id: 'c-new' }))
    api.getCustomer.mockResolvedValue(buildCustomer({ id: 'c-new' }))
    api.listAddresses.mockResolvedValue([])
    api.listContacts.mockResolvedValue([])
    const { wrapper, router } = await mountWithPlugins(App, { route: '/customers', user: seller })
    await flushPromises()

    await wrapper
      .findAll('button')
      .find((b) => b.text().includes('Novo cliente'))
      ?.trigger('click')
    const form = wrapper.find('#customer-form')
    const inputs = form.findAll('input')
    await inputs[0]?.setValue('Padaria Boa Ltda')
    await inputs[2]?.setValue('11.222.333/0001-81')
    await form.find('select').setValue('seg-1')
    await form.trigger('submit')
    await flushPromises()

    expect(api.createCustomer).toHaveBeenCalledWith({
      legal_name: 'Padaria Boa Ltda',
      trade_name: '',
      tax_id: '11.222.333/0001-81',
      email: '',
      phone: '',
      segment_id: 'seg-1',
    })
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/customers/c-new'))
    await flushPromises()
    expect(wrapper.text()).toContain('Nenhum endereço cadastrado')
  })

  it('shows an unavailable segment next to the segment field', async () => {
    api.createCustomer.mockRejectedValue(
      new ApiError({
        status: 422,
        code: 'SEGMENT_NOT_AVAILABLE',
        message: 'Segmento não encontrado ou inativo.',
        details: { field: 'segment_id' },
      }),
    )
    const { wrapper } = await mountWithPlugins(App, { route: '/customers', user: seller })
    await flushPromises()

    await wrapper
      .findAll('button')
      .find((b) => b.text().includes('Novo cliente'))
      ?.trigger('click')
    const form = wrapper.find('#customer-form')
    await form.findAll('input')[0]?.setValue('Padaria Boa Ltda')
    await form.findAll('input')[2]?.setValue('11222333000181')
    await form.find('select').setValue('seg-1')
    await form.trigger('submit')
    await flushPromises()

    const select = form.find('select')
    expect(select.attributes('aria-invalid')).toBe('true')
    expect(form.text()).toContain('Segmento não encontrado ou inativo.')
  })
})
