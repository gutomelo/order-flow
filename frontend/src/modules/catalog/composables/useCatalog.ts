import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'

import * as catalogApi from '@/modules/catalog/api/catalogApi'
import type { Category, ProductFilters, ProductInput } from '@/modules/catalog/types'

export const productsKeys = {
  all: ['products'] as const,
  list: (filters: ProductFilters) => [...productsKeys.all, 'list', filters] as const,
}

export const categoriesKeys = {
  all: ['categories'] as const,
}

export function useProductsList(filters: MaybeRefOrGetter<ProductFilters>) {
  return useQuery({
    queryKey: computed(() => productsKeys.list(toValue(filters))),
    queryFn: () => catalogApi.listProducts(toValue(filters)),
    placeholderData: keepPreviousData,
  })
}

export function useCategories() {
  return useQuery({ queryKey: categoriesKeys.all, queryFn: catalogApi.listCategories })
}

export function useSaveProduct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id?: string; data: ProductInput }) => {
      if (!id) return catalogApi.createProduct(data)
      // Edição não envia SKU: a identidade do produto não muda (regra C7).
      return catalogApi.updateProduct(id, {
        name: data.name,
        description: data.description,
        unit: data.unit,
        barcode: data.barcode,
        category_id: data.category_id,
        default_supplier_id: data.default_supplier_id,
      })
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: productsKeys.all }),
  })
}

export function useSetProductActive() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: { id: string; active: boolean }) =>
      catalogApi.setProductActive(input.id, input.active),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: productsKeys.all }),
  })
}

/** Mutações de categoria também afetam a listagem de produtos (caminho exibido). */
function useInvalidateCatalog() {
  const queryClient = useQueryClient()
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: categoriesKeys.all }),
      queryClient.invalidateQueries({ queryKey: productsKeys.all }),
    ])
}

export function useSaveCategory() {
  const invalidate = useInvalidateCatalog()
  return useMutation({
    mutationFn: ({ id, name, parentId }: { id?: string; name: string; parentId: string | null }) =>
      id
        ? catalogApi.updateCategory(id, { name, parent_id: parentId })
        : catalogApi.createCategory({ name, parent_id: parentId }),
    onSuccess: invalidate,
  })
}

export function useSetCategoryActive() {
  const invalidate = useInvalidateCatalog()
  return useMutation({
    mutationFn: (input: { id: string; active: boolean }) =>
      catalogApi.setCategoryActive(input.id, input.active),
    onSuccess: invalidate,
  })
}

/** IDs da categoria e de toda a sua subárvore (não pode ser destino de "mover"). */
export function subtreeIds(categories: Category[], rootId: string): Set<string> {
  const ids = new Set([rootId])
  let added = true
  while (added) {
    added = false
    for (const category of categories) {
      if (category.parent_id && ids.has(category.parent_id) && !ids.has(category.id)) {
        ids.add(category.id)
        added = true
      }
    }
  }
  return ids
}
