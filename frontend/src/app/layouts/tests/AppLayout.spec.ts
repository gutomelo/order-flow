import { flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import App from '@/App.vue'
import { mountWithPlugins } from '@/testing/mountWithPlugins'

vi.mock('@/modules/dashboard/api/healthApi', () => ({
  fetchReadiness: vi.fn(() => new Promise(() => {})),
}))

describe('AppLayout', () => {
  it('redirects to the dashboard and marks it as the current page', async () => {
    const { wrapper, router } = await mountWithPlugins(App, { route: '/' })
    await flushPromises()

    expect(router.currentRoute.value.name).toBe('dashboard')
    const current = wrapper.find('nav a[aria-current="page"]')
    expect(current.exists()).toBe(true)
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
})
