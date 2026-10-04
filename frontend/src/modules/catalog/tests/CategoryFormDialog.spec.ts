import { flushPromises } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import CategoryFormDialog from '@/modules/catalog/components/CategoryFormDialog.vue'
import type { Category } from '@/modules/catalog/types'
import { mountWithPlugins } from '@/testing/mountWithPlugins'

const tree: Category[] = [
  { id: 'a', name: 'Bebidas', parent_id: null, depth: 1, path: 'Bebidas', is_active: true },
  { id: 'b', name: 'Refri', parent_id: 'a', depth: 2, path: 'Bebidas › Refri', is_active: true },
  {
    id: 'c',
    name: 'Lata',
    parent_id: 'b',
    depth: 3,
    path: 'Bebidas › Refri › Lata',
    is_active: true,
  },
  { id: 'd', name: 'Limpeza', parent_id: null, depth: 1, path: 'Limpeza', is_active: true },
  { id: 'e', name: 'Antiga', parent_id: null, depth: 1, path: 'Antiga', is_active: false },
]

async function parentOptionsFor(category: Category | null) {
  const Host = defineComponent({
    setup: () => () => h(CategoryFormDialog, { open: ref(true).value, category, categories: tree }),
  })
  const { wrapper } = await mountWithPlugins(Host)
  await flushPromises()
  return wrapper.findAll('select option').map((option) => option.text())
}

describe('CategoryFormDialog parent options', () => {
  it('new categories cannot go under a third-level or inactive category', async () => {
    const options = await parentOptionsFor(null)

    expect(options).toEqual(['Nenhuma (nível principal)', 'Bebidas', 'Bebidas › Refri', 'Limpeza'])
  })

  it('a category cannot move into its own subtree or beyond three levels', async () => {
    // "Refri" tem um filho: só cabe sob categorias de nível 1 que não sejam ela mesma/descendentes.
    const refri = tree[1] as Category
    const options = await parentOptionsFor(refri)

    expect(options).toEqual(['Nenhuma (nível principal)', 'Bebidas', 'Limpeza'])
  })
})
