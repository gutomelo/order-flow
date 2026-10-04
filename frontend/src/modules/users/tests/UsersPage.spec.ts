import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App.vue'
import * as usersApi from '@/modules/users/api/usersApi'
import type { User } from '@/modules/users/types'
import { ApiError } from '@/services/http/apiError'
import { mountWithPlugins } from '@/testing/mountWithPlugins'

vi.mock('@/modules/users/api/usersApi', async (importOriginal) => ({
  ...(await importOriginal<typeof usersApi>()),
  listUsers: vi.fn(),
  listTeams: vi.fn(),
  setUserActive: vi.fn(),
  createUser: vi.fn(),
}))

const api = vi.mocked(usersApi)

function buildUser(overrides: Partial<User> = {}): User {
  return {
    id: 'user-2',
    email: 'bruno@acme.com',
    first_name: 'Bruno',
    last_name: 'Lima',
    full_name: 'Bruno Lima',
    role: 'SALES',
    team: null,
    is_active: true,
    last_login: null,
    date_joined: '2026-10-01T12:00:00Z',
    ...overrides,
  }
}

const page = (results: User[]) => ({ count: results.length, next: null, previous: null, results })

describe('UsersPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.listTeams.mockResolvedValue(page([]) as never)
  })

  it('lists users with role and status as text', async () => {
    api.listUsers.mockResolvedValue(page([buildUser()]))

    const { wrapper } = await mountWithPlugins(App, { route: '/users' })
    await flushPromises()

    const row = wrapper.find('tbody tr')
    expect(row.text()).toContain('Bruno Lima')
    expect(row.text()).toContain('Vendas')
    expect(row.text()).toContain('Ativo')
    expect(row.text()).toContain('Nunca acessou')
  })

  it('reads filters from the URL', async () => {
    api.listUsers.mockResolvedValue(page([]))

    await mountWithPlugins(App, { route: '/users?role=FINANCE&status=inactive&search=ana' })
    await flushPromises()

    expect(api.listUsers).toHaveBeenCalledWith({
      page: 1,
      search: 'ana',
      role: 'FINANCE',
      status: 'inactive',
    })
  })

  it('explains empty results when filters are applied', async () => {
    api.listUsers.mockResolvedValue(page([]))

    const { wrapper } = await mountWithPlugins(App, { route: '/users?role=FINANCE' })
    await flushPromises()

    expect(wrapper.text()).toContain('Nenhum usuário encontrado')
    expect(wrapper.text()).toContain('Ajuste a busca ou os filtros')
  })

  it('shows an error state with retry when the list fails', async () => {
    api.listUsers.mockRejectedValue(
      new ApiError({ status: null, code: 'NETWORK_ERROR', message: '' }),
    )

    const { wrapper } = await mountWithPlugins(App, { route: '/users' })
    await flushPromises()

    expect(wrapper.text()).toContain('Não foi possível carregar os usuários')
    expect(wrapper.text()).toContain('Tentar novamente')
  })

  it('asks for confirmation before deactivating a user', async () => {
    api.listUsers.mockResolvedValue(page([buildUser()]))
    api.setUserActive.mockResolvedValue(buildUser({ is_active: false }))

    const { wrapper } = await mountWithPlugins(App, { route: '/users' })
    await flushPromises()

    const deactivate = wrapper
      .findAll('tbody button')
      .find((button) => button.text().includes('Desativar Bruno Lima'))
    await deactivate?.trigger('click')
    await flushPromises()
    expect(api.setUserActive).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Desativar Bruno Lima?')

    const confirm = wrapper
      .findAll('dialog button')
      .find((button) => button.text() === 'Desativar usuário')
    await confirm?.trigger('click')
    await flushPromises()

    expect(api.setUserActive).toHaveBeenCalledWith('user-2', false)
    expect(wrapper.text()).toContain('Usuário desativado.')
  })

  it('does not offer self-deactivation', async () => {
    api.listUsers.mockResolvedValue(page([buildUser({ id: 'user-1', full_name: 'Ana Souza' })]))

    const { wrapper } = await mountWithPlugins(App, { route: '/users' })
    await flushPromises()

    expect(wrapper.find('tbody').text()).toContain('(você)')
    const labels = wrapper.findAll('tbody button').map((button) => button.text())
    expect(labels.some((label) => label.includes('Desativar'))).toBe(false)
  })

  it('maps backend validation errors to the form fields', async () => {
    api.listUsers.mockResolvedValue(page([]))
    api.createUser.mockRejectedValue(
      new ApiError({
        status: 400,
        code: 'VALIDATION_ERROR',
        message: 'Os dados enviados são inválidos.',
        details: { fields: { password: ['Esta senha é muito comum.'] } },
      }),
    )
    const { wrapper } = await mountWithPlugins(App, { route: '/users' })
    await flushPromises()

    await wrapper
      .findAll('button')
      .find((button) => button.text().includes('Novo usuário'))
      ?.trigger('click')
    await flushPromises()
    await wrapper.findAll('dialog input')[0]?.setValue('Carla') // nome
    await wrapper.find('dialog input[type="email"]').setValue('carla@acme.com')
    await wrapper.find('dialog input[type="password"]').setValue('senha12345')
    await wrapper.find('#user-form').trigger('submit')
    await flushPromises()

    const password = wrapper.find('dialog input[type="password"]')
    expect(wrapper.find('dialog').text()).toContain('Esta senha é muito comum.')
    expect(password.attributes('aria-invalid')).toBe('true')
  })
})
