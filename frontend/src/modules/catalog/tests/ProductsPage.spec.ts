import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App.vue'
import * as catalogApi from '@/modules/catalog/api/catalogApi'
import type { Product } from '@/modules/catalog/types'
import * as suppliersApi from '@/modules/suppliers/api/suppliersApi'
import { buildCurrentUser, mountWithPlugins } from '@/testing/mountWithPlugins'

vi.mock('@/modules/catalog/api/catalogApi', async (importOriginal) => ({
  ...(await importOriginal<typeof catalogApi>()),
  listProducts: vi.fn(),
  listCategories: vi.fn(),
}))
vi.mock('@/modules/suppliers/api/suppliersApi', async (importOriginal) => ({
  ...(await importOriginal<typeof suppliersApi>()),
  listActiveSupplierOptions: vi.fn(),
}))

const catalog = vi.mocked(catalogApi)
const suppliers = vi.mocked(suppliersApi)

const manager = buildCurrentUser({
  role: 'MANAGER',
  permissions: ['catalog:read', 'catalog:manage', 'suppliers:read'],
})
const sales = buildCurrentUser({ role: 'SALES', permissions: ['catalog:read'] })

function buildProduct(overrides: Partial<Product> = {}): Product {
  return {
    id: 'p-1',
    sku: 'BEV-COLA-350',
    name: 'Refrigerante Cola 350ml',
    description: '',
    unit: 'BOX',
    barcode: '',
    category: {
      id: 'c-2',
      name: 'Refrigerantes',
      path: 'Bebidas › Refrigerantes',
      is_active: true,
    },
    default_supplier: { id: 's-1', display_name: 'Sul Express', is_active: false },
    is_active: true,
    created_at: '2026-10-01T12:00:00Z',
    updated_at: '2026-10-01T12:00:00Z',
    ...overrides,
  }
}

const page = (results: Product[]) => ({
  count: results.length,
  next: null,
  previous: null,
  results,
})

describe('ProductsPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    catalog.listCategories.mockResolvedValue([
      { id: 'c-1', name: 'Bebidas', parent_id: null, depth: 1, path: 'Bebidas', is_active: true },
    ])
    suppliers.listActiveSupplierOptions.mockResolvedValue([])
  })

  it('shows SKU, category path, unit and an inactive default supplier', async () => {
    catalog.listProducts.mockResolvedValue(page([buildProduct()]))

    const { wrapper } = await mountWithPlugins(App, { route: '/products', user: manager })
    await flushPromises()

    const row = wrapper.find('tbody tr').text()
    expect(row).toContain('BEV-COLA-350')
    expect(row).toContain('Bebidas › Refrigerantes')
    expect(row).toContain('Caixa')
    expect(row).toContain('Sul Express (inativo)')
  })

  it('sends filters read from the URL to the API', async () => {
    catalog.listProducts.mockResolvedValue(page([]))

    await mountWithPlugins(App, {
      route: '/products?category=c-1&status=inactive&search=cola',
      user: manager,
    })
    await flushPromises()

    expect(catalog.listProducts).toHaveBeenCalledWith({
      page: 1,
      search: 'cola',
      category: 'c-1',
      supplier: '',
      status: 'inactive',
    })
  })

  it('hides management actions and suppliers for read-only roles', async () => {
    catalog.listProducts.mockResolvedValue(page([buildProduct()]))

    const { wrapper } = await mountWithPlugins(App, { route: '/products', user: sales })
    await flushPromises()

    expect(wrapper.text()).not.toContain('Novo produto')
    expect(wrapper.find('tbody').text()).not.toContain('Sul Express')
    expect(wrapper.findAll('tbody button')).toHaveLength(0)
    // Sem `suppliers:read`, a página nem consulta fornecedores (evita 403).
    expect(suppliers.listActiveSupplierOptions).not.toHaveBeenCalled()
  })

  it('explains the empty catalog differently for read-only users', async () => {
    catalog.listProducts.mockResolvedValue(page([]))

    const { wrapper } = await mountWithPlugins(App, { route: '/products', user: sales })
    await flushPromises()

    expect(wrapper.text()).toContain('Quando o catálogo for cadastrado')
  })
})
