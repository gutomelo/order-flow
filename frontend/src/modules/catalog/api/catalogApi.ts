import type { Category, Product, ProductFilters, ProductInput } from '@/modules/catalog/types'
import { http } from '@/services/http/client'
import type { Paginated } from '@/types/api'

export const PRODUCTS_PAGE_SIZE = 25

export async function listProducts(filters: ProductFilters) {
  const params: Record<string, string | number | boolean> = {
    page: filters.page,
    page_size: PRODUCTS_PAGE_SIZE,
  }
  if (filters.search) params.search = filters.search
  if (filters.category) params.category = filters.category
  if (filters.supplier) params.supplier = filters.supplier
  if (filters.status) params.is_active = filters.status === 'active'
  const { data } = await http.get<Paginated<Product>>('/products', { params })
  return data
}

export async function createProduct(input: ProductInput) {
  const { data } = await http.post<Product>('/products', input)
  return data
}

/** SKU não é enviado: a identidade do produto não muda (regra C7). */
export async function updateProduct(id: string, input: Omit<ProductInput, 'sku'>) {
  const { data } = await http.patch<Product>(`/products/${id}`, input)
  return data
}

export async function setProductActive(id: string, active: boolean) {
  const { data } = await http.post<Product>(`/products/${id}/${active ? 'activate' : 'deactivate'}`)
  return data
}

/** Árvore inteira (achatada, pai antes dos filhos) — sem paginação, limitada a 3 níveis. */
export async function listCategories() {
  const { data } = await http.get<Category[]>('/categories')
  return data
}

export async function createCategory(input: { name: string; parent_id: string | null }) {
  const { data } = await http.post<Category>('/categories', input)
  return data
}

export async function updateCategory(
  id: string,
  input: { name?: string; parent_id?: string | null },
) {
  const { data } = await http.patch<Category>(`/categories/${id}`, input)
  return data
}

export async function setCategoryActive(id: string, active: boolean) {
  const { data } = await http.post<Category>(
    `/categories/${id}/${active ? 'activate' : 'deactivate'}`,
  )
  return data
}
