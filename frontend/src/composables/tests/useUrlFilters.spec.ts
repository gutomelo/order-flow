import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import { useUrlFilters } from '@/composables/useUrlFilters'

interface Filters {
  page: number
  search: string
  status: '' | 'active' | 'inactive'
}

async function setup(initialUrl: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/items', component: { render: () => null } }],
  })
  await router.push(initialUrl)
  let api!: ReturnType<typeof useUrlFilters<Filters>>
  mount(
    defineComponent({
      setup() {
        api = useUrlFilters<Filters>(
          { page: 1, search: '', status: '' },
          { status: (raw) => (raw === 'active' || raw === 'inactive' ? raw : undefined) },
        )
        return () => h('div')
      },
    }),
    { global: { plugins: [router] } },
  )
  return { router, api }
}

describe('useUrlFilters', () => {
  it('reads filters from the query string, ignoring invalid values', async () => {
    const { api } = await setup('/items?search=cafe&status=archived&page=3')

    expect(api.filters.value).toEqual({ page: 3, search: 'cafe', status: '' })
  })

  it('writes only non-default values and resets the page when a filter changes', async () => {
    const { api, router } = await setup('/items?page=4')

    api.update({ status: 'active' })
    await nextTick()
    await router.isReady()
    await new Promise((resolve) => setTimeout(resolve))

    expect(router.currentRoute.value.query).toEqual({ status: 'active' })
    expect(api.hasActiveFilters.value).toBe(true)
  })

  it('keeps other filters when only the page changes', async () => {
    const { api, router } = await setup('/items?search=cafe')

    api.field('page').value = 2
    await new Promise((resolve) => setTimeout(resolve))

    expect(router.currentRoute.value.query).toEqual({ search: 'cafe', page: '2' })
  })
})
