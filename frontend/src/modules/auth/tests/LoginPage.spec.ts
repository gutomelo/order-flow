import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App.vue'
import * as authApi from '@/modules/auth/api/authApi'
import { ApiError } from '@/services/http/apiError'
import { buildCurrentUser, mountWithPlugins } from '@/testing/mountWithPlugins'

vi.mock('@/modules/auth/api/authApi')
vi.mock('@/modules/dashboard/api/healthApi', () => ({
  fetchReadiness: vi.fn(() => new Promise(() => {})),
}))

const api = vi.mocked(authApi)

async function fillAndSubmit(wrapper: Awaited<ReturnType<typeof mountWithPlugins>>['wrapper']) {
  await wrapper.find('input[type="email"]').setValue('ana@acme.com')
  await wrapper.find('input[type="password"]').setValue('Pedido-Seguro-2026!')
  await wrapper.find('form').trigger('submit')
  await flushPromises()
}

describe('LoginPage', () => {
  beforeEach(() => vi.resetAllMocks())

  it('validates required fields before calling the API', async () => {
    const { wrapper } = await mountWithPlugins(App, { route: '/login', user: null })

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('Informe um e-mail válido.')
    expect(wrapper.text()).toContain('Campo obrigatório.')
    expect(api.login).not.toHaveBeenCalled()
    const email = wrapper.find('input[type="email"]')
    expect(email.attributes('aria-invalid')).toBe('true')
    expect(email.attributes('aria-describedby')).toBeTruthy()
  })

  it('shows the backend message when credentials are rejected', async () => {
    api.login.mockRejectedValue(
      new ApiError({
        status: 401,
        code: 'INVALID_CREDENTIALS',
        message: 'E-mail ou senha inválidos.',
      }),
    )
    const { wrapper } = await mountWithPlugins(App, { route: '/login', user: null })

    await fillAndSubmit(wrapper)

    expect(wrapper.find('[role="alert"]').text()).toContain('E-mail ou senha inválidos.')
  })

  it('returns to the page the user originally requested', async () => {
    api.login.mockResolvedValue({ access: 'a', user: buildCurrentUser() })
    const { wrapper, router } = await mountWithPlugins(App, {
      route: '/login?redirect=/teams',
      user: null,
    })

    await fillAndSubmit(wrapper)

    // A rota de destino é carregada sob demanda (import dinâmico).
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/teams'))
  })

  it('ignores external redirect targets (open redirect)', async () => {
    api.login.mockResolvedValue({ access: 'a', user: buildCurrentUser() })
    const { wrapper, router } = await mountWithPlugins(App, {
      route: '/login?redirect=//evil.example.com',
      user: null,
    })

    await fillAndSubmit(wrapper)

    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('dashboard'))
  })
})
