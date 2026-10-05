import { flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import App from '@/App.vue'
import { buildCurrentUser, mountWithPlugins } from '@/testing/mountWithPlugins'

vi.mock('@/modules/dashboard/api/healthApi', () => ({
  fetchReadiness: vi.fn(() => new Promise(() => {})),
}))
vi.mock('@/modules/users/api/usersApi', () => ({
  USERS_PAGE_SIZE: 25,
  listUsers: vi.fn(() => new Promise(() => {})),
  listTeams: vi.fn(() => new Promise(() => {})),
}))

const viewer = buildCurrentUser({ role: 'VIEWER', permissions: ['orders:read'] })

describe('AppLayout', () => {
  it('redirects to the dashboard and marks it as the current page', async () => {
    const { wrapper, router } = await mountWithPlugins(App, { route: '/' })
    await flushPromises()

    expect(router.currentRoute.value.name).toBe('dashboard')
    const current = wrapper.find('nav a[aria-current="page"]')
    expect(current.text()).toContain('Dashboard')
    expect(wrapper.find('h1').text()).toBe('Dashboard')
  })

  it('collapses the sidebar and exposes the state to assistive technology', async () => {
    const { wrapper } = await mountWithPlugins(App, { route: '/dashboard' })
    await flushPromises()

    const toggle = wrapper.find('button[aria-controls="app-sidebar"]')
    expect(toggle.attributes('aria-expanded')).toBe('true')

    await toggle.trigger('click')

    expect(toggle.attributes('aria-expanded')).toBe('false')
  })

  it('shows a helpful not-found page for unknown routes', async () => {
    const { wrapper } = await mountWithPlugins(App, { route: '/does-not-exist' })
    await flushPromises()

    expect(wrapper.text()).toContain('Página não encontrada')
    expect(wrapper.find('a[href="/dashboard"]').exists()).toBe(true)
  })

  it('sends visitors to the login page, remembering where they wanted to go', async () => {
    const { router } = await mountWithPlugins(App, { route: '/users?role=SALES', user: null })

    expect(router.currentRoute.value.name).toBe('login')
    expect(router.currentRoute.value.query.redirect).toBe('/users?role=SALES')
  })

  it('blocks pages that require a permission the user does not have', async () => {
    const { router, wrapper } = await mountWithPlugins(App, { route: '/users', user: viewer })
    await flushPromises()

    expect(router.currentRoute.value.name).toBe('forbidden')
    expect(wrapper.text()).toContain('Acesso não permitido')
  })

  it('only shows navigation items the user is allowed to use', async () => {
    const admin = await mountWithPlugins(App, { route: '/dashboard' })
    const restricted = await mountWithPlugins(App, { route: '/dashboard', user: viewer })
    await flushPromises()

    const links = (wrapper: typeof admin.wrapper) =>
      wrapper.findAll('aside nav a').map((link) => link.text())
    expect(links(admin.wrapper)).toEqual(['Dashboard', 'Pedidos', 'Usuários', 'Equipes'])
    expect(links(restricted.wrapper)).toEqual(['Dashboard', 'Pedidos'])
  })

  it('shows the signed-in user and organization in the user menu', async () => {
    const { wrapper } = await mountWithPlugins(App, { route: '/dashboard' })
    await flushPromises()

    await wrapper.find('button[aria-controls]:not([aria-controls="app-sidebar"])').trigger('click')

    expect(wrapper.text()).toContain('Acme Distribuidora · Administrador')
  })
})
