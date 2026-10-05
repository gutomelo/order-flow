import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App.vue'
import * as customersApi from '@/modules/customers/api/customersApi'
import { buildAddress, buildContact, buildCustomer } from '@/modules/customers/tests/fixtures'
import { ApiError } from '@/services/http/apiError'
import { buildCurrentUser, mountWithPlugins } from '@/testing/mountWithPlugins'

vi.mock('@/modules/customers/api/customersApi', async (importOriginal) => ({
  ...(await importOriginal<typeof customersApi>()),
  getCustomer: vi.fn(),
  listAddresses: vi.fn(),
  listContacts: vi.fn(),
  listSegmentOptions: vi.fn(),
  setAddressRole: vi.fn(),
  removeAddress: vi.fn(),
  saveContact: vi.fn(),
}))

const api = vi.mocked(customersApi)
const seller = buildCurrentUser({
  role: 'SALES',
  permissions: ['customers:read', 'customers:create', 'customers:update'],
})
const viewer = buildCurrentUser({ role: 'VIEWER', permissions: ['customers:read'] })

const ROUTE = '/customers/c-1'

function buttonNamed(
  wrapper: Awaited<ReturnType<typeof mountWithPlugins>>['wrapper'],
  name: string,
) {
  const button = wrapper.findAll('button').find((b) => b.text().includes(name))
  if (!button) throw new Error(`button "${name}" not found`)
  return button
}

describe('CustomerDetailPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.getCustomer.mockResolvedValue(buildCustomer())
    api.listSegmentOptions.mockResolvedValue([])
    api.listAddresses.mockResolvedValue([
      buildAddress(),
      buildAddress({
        id: 'a-2',
        label: 'Filial Campinas',
        city: 'Campinas',
        is_billing: false,
        is_default_shipping: false,
      }),
    ])
    api.listContacts.mockResolvedValue([buildContact()])
  })

  it('shows the customer, addresses with their roles as text and the primary contact', async () => {
    const { wrapper } = await mountWithPlugins(App, { route: ROUTE, user: seller })
    await flushPromises()

    expect(wrapper.find('h1').text()).toBe('Mercado Central')
    const [main, branch] = wrapper.findAll('article')
    expect(main?.text()).toContain('Cobrança')
    expect(main?.text()).toContain('Entrega padrão')
    expect(main?.text()).toContain('CEP 01310-100')
    expect(branch?.text()).not.toContain('Cobrança')
    expect(wrapper.text()).toContain('Principal')
  })

  it('moves the default shipping role to another address', async () => {
    api.setAddressRole.mockResolvedValue(buildAddress({ id: 'a-2' }))
    const { wrapper } = await mountWithPlugins(App, { route: ROUTE, user: seller })
    await flushPromises()

    await buttonNamed(wrapper, 'Tornar entrega padrão').trigger('click')
    await flushPromises()

    expect(api.setAddressRole).toHaveBeenCalledWith('c-1', 'a-2', 'default-shipping')
    expect(wrapper.text()).toContain('Filial Campinas agora é o endereço de entrega padrão.')
    // Os papéis vêm do servidor: a lista é recarregada após a mudança.
    expect(api.listAddresses.mock.calls.length).toBeGreaterThan(1)
  })

  it('warns that roles move when removing a role holder and shows failures inside the dialog', async () => {
    api.removeAddress.mockRejectedValue(
      new ApiError({ status: 500, code: 'INTERNAL_ERROR', message: 'Erro inesperado.' }),
    )
    const { wrapper } = await mountWithPlugins(App, { route: ROUTE, user: seller })
    await flushPromises()

    await wrapper
      .findAll('article')[0]
      ?.findAll('button')
      .find((b) => b.text().includes('Remover'))
      ?.trigger('click')
    await flushPromises()
    const dialog = wrapper
      .findAll('dialog')
      .find((d) => d.text().includes('Remover o endereço Matriz?'))
    if (!dialog) throw new Error('confirm dialog not found')
    expect(dialog.text()).toContain('passam para o endereço mais antigo restante')

    await dialog
      .findAll('button')
      .find((b) => b.text() === 'Remover')
      ?.trigger('click')
    await flushPromises()

    expect(api.removeAddress).toHaveBeenCalledWith('c-1', 'a-1')
    expect(dialog.find('[role="alert"]').text()).toContain('Erro inesperado.')
  })

  it('requires an email or a phone for contacts before calling the API', async () => {
    const { wrapper } = await mountWithPlugins(App, { route: ROUTE, user: seller })
    await flushPromises()

    await buttonNamed(wrapper, 'Novo contato').trigger('click')
    const form = wrapper.find('#contact-form')
    await form.findAll('input')[0]?.setValue('Rui Costa')
    await form.trigger('submit')
    await flushPromises()

    expect(form.text()).toContain('Informe ao menos um e-mail ou telefone.')
    expect(api.saveContact).not.toHaveBeenCalled()
  })

  it('hides every editing action from read-only roles', async () => {
    const { wrapper } = await mountWithPlugins(App, { route: ROUTE, user: viewer })
    await flushPromises()

    const labels = wrapper.findAll('main button').map((b) => b.text())
    expect(labels.some((l) => /Editar|Remover|Tornar|Novo|Inativar/.test(l))).toBe(false)
  })

  it('explains when the customer does not exist', async () => {
    api.getCustomer.mockRejectedValue(
      new ApiError({ status: 404, code: 'NOT_FOUND', message: 'Não encontrado.' }),
    )
    const { wrapper } = await mountWithPlugins(App, { route: ROUTE, user: seller })
    await flushPromises()

    expect(wrapper.text()).toContain('Cliente não encontrado')
    expect(api.listAddresses).not.toHaveBeenCalled()
  })
})
