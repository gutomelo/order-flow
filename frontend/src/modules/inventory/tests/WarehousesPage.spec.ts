import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App.vue'
import * as inventoryApi from '@/modules/inventory/api/inventoryApi'
import { ApiError } from '@/services/http/apiError'
import { buildCurrentUser, mountWithPlugins } from '@/testing/mountWithPlugins'

vi.mock('@/modules/inventory/api/inventoryApi', async (importOriginal) => ({
  ...(await importOriginal<typeof inventoryApi>()),
  listWarehouses: vi.fn(),
  setWarehouseActive: vi.fn(),
}))

const api = vi.mocked(inventoryApi)
const manager = buildCurrentUser({
  role: 'WAREHOUSE',
  permissions: ['inventory:read', 'inventory:update'],
})

async function confirmDeactivation() {
  const mounted = await mountWithPlugins(App, { route: '/warehouses', user: manager })
  await flushPromises()
  await mounted.wrapper
    .findAll('tbody button')
    .find((button) => button.text().includes('Inativar CD-RJ'))
    ?.trigger('click')
  await flushPromises()
  const dialog = mounted.wrapper
    .findAll('dialog')
    .find((candidate) => candidate.text().includes('Inativar CD-RJ?'))
  if (!dialog) throw new Error('confirm dialog not found')
  await dialog
    .findAll('button')
    .find((button) => button.text() === 'Inativar')
    ?.trigger('click')
  await flushPromises()
  return { ...mounted, dialog }
}

describe('WarehousesPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.listWarehouses.mockResolvedValue([
      {
        id: 'w-rj',
        code: 'CD-RJ',
        name: 'CD Rio de Janeiro',
        is_active: true,
        created_at: '',
        updated_at: '',
      },
    ])
  })

  it('keeps the confirmation open and explains why a stocked warehouse cannot be deactivated', async () => {
    api.setWarehouseActive.mockRejectedValue(
      new ApiError({
        status: 409,
        code: 'WAREHOUSE_HAS_STOCK',
        message: 'Zere o saldo do depósito antes de inativá-lo.',
      }),
    )

    const { dialog } = await confirmDeactivation()

    // Com o <dialog> modal aberto o toast ficaria inerte atrás do backdrop: o erro vai no diálogo.
    expect(dialog.find('[role="alert"]').text()).toContain('Zere o saldo do depósito')
  })
})
