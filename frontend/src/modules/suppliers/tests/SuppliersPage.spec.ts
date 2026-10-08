import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App.vue'
import * as suppliersApi from '@/modules/suppliers/api/suppliersApi'
import type { Supplier } from '@/modules/suppliers/types'
import { buildCurrentUser, mountWithPlugins } from '@/testing/mountWithPlugins'

vi.mock('@/modules/suppliers/api/suppliersApi', async (importOriginal) => ({
  ...(await importOriginal<typeof suppliersApi>()),
  listSuppliers: vi.fn(),
  createSupplier: vi.fn(),
}))

const api = vi.mocked(suppliersApi)
const manager = buildCurrentUser({
  role: 'MANAGER',
  permissions: ['suppliers:read', 'suppliers:manage'],
})

const supplier: Supplier = {
  id: 's-1',
  legal_name: 'Distribuidora Sul Ltda',
  trade_name: 'Sul Express',
  display_name: 'Sul Express',
  tax_id: '12ABC34501DE35',
  tax_id_formatted: '12.ABC.345/01DE-35',
  email: 'compras@sul.com',
  phone: '',
  is_active: true,
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
}

async function openCreateDialog() {
  const mounted = await mountWithPlugins(App, { route: '/suppliers', user: manager })
  await flushPromises()
  await mounted.wrapper
    .findAll('button')
    .find((button) => button.text().includes('Novo fornecedor'))
    ?.trigger('click')
  await flushPromises()
  return mounted
}

describe('SuppliersPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.listSuppliers.mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [supplier],
    })
  })

  it('lists suppliers with the formatted alphanumeric CNPJ', async () => {
    const { wrapper } = await mountWithPlugins(App, { route: '/suppliers', user: manager })
    await flushPromises()

    const row = wrapper.find('tbody tr').text()
    expect(row).toContain('Sul Express')
    expect(row).toContain('Distribuidora Sul Ltda')
    expect(row).toContain('12.ABC.345/01DE-35')
  })

  it('rejects an invalid CNPJ before calling the API', async () => {
    const { wrapper } = await openCreateDialog()

    const inputs = wrapper.findAll('dialog input')
    await inputs[0]?.setValue('Nova Fornecedora Ltda')
    await inputs[2]?.setValue('11.222.333/0001-82')
    await wrapper.find('#supplier-form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('dialog').text()).toContain('Informe um CNPJ válido')
    expect(api.createSupplier).not.toHaveBeenCalled()
  })

  it('creates a supplier with a valid alphanumeric CNPJ', async () => {
    api.createSupplier.mockResolvedValue(supplier)
    const { wrapper } = await openCreateDialog()

    const inputs = wrapper.findAll('dialog input')
    await inputs[0]?.setValue('Distribuidora Sul Ltda')
    await inputs[2]?.setValue('12.ABC.345/01DE-35')
    await wrapper.find('#supplier-form').trigger('submit')
    await flushPromises()

    expect(api.createSupplier).toHaveBeenCalledWith(
      expect.objectContaining({
        legal_name: 'Distribuidora Sul Ltda',
        tax_id: '12.ABC.345/01DE-35',
      }),
    )
    expect(wrapper.text()).toContain('Fornecedor criado.')
  })
})
