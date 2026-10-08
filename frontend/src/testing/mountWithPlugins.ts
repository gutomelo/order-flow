import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import type { Component } from 'vue'
import { createMemoryHistory } from 'vue-router'

import { createAppI18n } from '@/app/providers/i18n'
import { createAppRouter } from '@/app/router'
import { useSessionStore } from '@/modules/auth/stores/session'
import type { CurrentUser, Role } from '@/modules/auth/types'

export function buildCurrentUser(overrides: Partial<CurrentUser> = {}): CurrentUser {
  return {
    id: 'user-1',
    email: 'ana@acme.com',
    first_name: 'Ana',
    last_name: 'Souza',
    full_name: 'Ana Souza',
    role: 'ADMIN' as Role,
    team: null,
    organization: { id: 'org-1', name: 'Acme Distribuidora', slug: 'acme' },
    permissions: ['users:manage', 'orders:read'],
    ...overrides,
  }
}

/**
 * Monta um componente com os mesmos plugins da aplicação (router em memória, sem retries).
 * `user`: sessão já autenticada; `null`: visitante (a restauração de sessão não é tentada).
 */
export async function mountWithPlugins(
  component: Component,
  options: { route?: string; user?: CurrentUser | null } = {},
) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const session = useSessionStore()
  session.restored = true
  if (options.user !== null) {
    session.user = options.user ?? buildCurrentUser()
    session.accessToken = 'test-access-token'
  }

  const router = createAppRouter(createMemoryHistory())
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

  await router.push(options.route ?? '/')
  await router.isReady()

  const wrapper = mount(component, {
    global: {
      plugins: [pinia, router, createAppI18n(), [VueQueryPlugin, { queryClient }]],
    },
    attachTo: document.body,
  })

  return { wrapper, router, queryClient, session }
}
