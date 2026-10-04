import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import type { Component } from 'vue'
import { createMemoryHistory } from 'vue-router'

import { createAppI18n } from '@/app/providers/i18n'
import { createAppRouter } from '@/app/router'

/** Monta um componente com os mesmos plugins da aplicação (router em memória, sem retries). */
export async function mountWithPlugins(component: Component, options: { route?: string } = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
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

  return { wrapper, router, queryClient }
}
