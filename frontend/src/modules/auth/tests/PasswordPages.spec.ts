import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App.vue'
import * as authApi from '@/modules/auth/api/authApi'
import { ApiError } from '@/services/http/apiError'
import { mountWithPlugins } from '@/testing/mountWithPlugins'

vi.mock('@/modules/auth/api/authApi')

const api = vi.mocked(authApi)
const LINK = '/reset-password#uid=MTIz&token=abc-123'

type Wrapper = Awaited<ReturnType<typeof mountWithPlugins>>['wrapper']
async function submitPasswords(wrapper: Wrapper, password: string, confirmation = password) {
  const [first, second] = wrapper.findAll('input[type="password"]')
  await first?.setValue(password)
  await second?.setValue(confirmation)
  await wrapper.find('form').trigger('submit')
  await flushPromises()
}

describe('forgot password', () => {
  beforeEach(() => vi.resetAllMocks())

  it('is reachable from the login page', async () => {
    const { wrapper, router } = await mountWithPlugins(App, { route: '/login', user: null })

    await wrapper.find('a[href="/forgot-password"]').trigger('click')

    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('forgot-password'))
  })

  it('answers the same way whether the account exists or not', async () => {
    api.requestPasswordReset.mockResolvedValue()
    const { wrapper } = await mountWithPlugins(App, { route: '/forgot-password', user: null })

    await wrapper.find('input[type="email"]').setValue('ana@acme.com')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(api.requestPasswordReset).toHaveBeenCalledWith('ana@acme.com')
    expect(wrapper.find('main [role="status"]').text()).toContain(
      'Se houver uma conta ativa para ana@acme.com, enviamos um link',
    )
  })

  it('shows the throttling message', async () => {
    api.requestPasswordReset.mockRejectedValue(
      new ApiError({ status: 429, code: 'RATE_LIMITED', message: 'Muitas tentativas.' }),
    )
    const { wrapper } = await mountWithPlugins(App, { route: '/forgot-password', user: null })

    await wrapper.find('input[type="email"]').setValue('ana@acme.com')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
  })
})

describe('reset password', () => {
  beforeEach(() => vi.resetAllMocks())

  it('sets the password with the link from the email and goes to login', async () => {
    api.confirmPasswordReset.mockResolvedValue()
    const { wrapper, router } = await mountWithPlugins(App, { route: LINK, user: null })

    await submitPasswords(wrapper, 'Outra-Senha-Forte-2026!')

    expect(api.confirmPasswordReset).toHaveBeenCalledWith({
      uid: 'MTIz',
      token: 'abc-123',
      password: 'Outra-Senha-Forte-2026!',
    })
    expect(router.currentRoute.value.name).toBe('login')
    expect(wrapper.text()).toContain('Senha definida. Entre com a nova senha.')
  })

  it('removes the token from the address bar once read', async () => {
    const { router } = await mountWithPlugins(App, { route: LINK, user: null })
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe('/reset-password')
  })

  it('checks the confirmation before calling the API', async () => {
    const { wrapper } = await mountWithPlugins(App, { route: LINK, user: null })

    await submitPasswords(wrapper, 'Outra-Senha-Forte-2026!', 'Outra-Senha')

    expect(api.confirmPasswordReset).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('As senhas não são iguais.')
  })

  it('shows the password policy reasons on the field', async () => {
    api.confirmPasswordReset.mockRejectedValue(
      new ApiError({
        status: 422,
        code: 'WEAK_PASSWORD',
        message: 'Esta senha é muito comum.',
        details: { field: 'password', reasons: ['Esta senha é muito comum.'] },
      }),
    )
    const { wrapper } = await mountWithPlugins(App, { route: LINK, user: null })

    await submitPasswords(wrapper, 'senha12345')

    const field = wrapper.findAll('input[type="password"]')[0]
    expect(field?.attributes('aria-invalid')).toBe('true')
    expect(wrapper.text()).toContain('Esta senha é muito comum.')
  })

  it('offers a new link when this one expired or was used', async () => {
    api.confirmPasswordReset.mockRejectedValue(
      new ApiError({
        status: 400,
        code: 'INVALID_PASSWORD_RESET_TOKEN',
        message: 'Este link expirou ou já foi usado.',
      }),
    )
    const { wrapper } = await mountWithPlugins(App, { route: LINK, user: null })

    await submitPasswords(wrapper, 'Outra-Senha-Forte-2026!')

    expect(wrapper.find('[role="alert"]').text()).toContain('Este link expirou ou já foi usado.')
    expect(wrapper.find('a[href="/forgot-password"]').exists()).toBe(true)
  })

  it('treats a link without token as invalid', async () => {
    const { wrapper } = await mountWithPlugins(App, { route: '/reset-password', user: null })

    expect(wrapper.find('form').exists()).toBe(false)
    expect(wrapper.text()).toContain('Pedir um novo link')
  })
})
