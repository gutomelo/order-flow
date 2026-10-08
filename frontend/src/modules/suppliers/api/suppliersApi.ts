import type { Supplier, SupplierFilters, SupplierInput } from '@/modules/suppliers/types'
import { http } from '@/services/http/client'
import type { Paginated } from '@/types/api'

export const SUPPLIERS_PAGE_SIZE = 25

export async function listSuppliers(filters: SupplierFilters) {
  const params: Record<string, string | number | boolean> = {
    page: filters.page,
    page_size: SUPPLIERS_PAGE_SIZE,
  }
  if (filters.search) params.search = filters.search
  if (filters.status) params.is_active = filters.status === 'active'
  const { data } = await http.get<Paginated<Supplier>>('/suppliers', { params })
  return data
}

/** Opções para seletores (até 100). Volumes maiores pedem um combobox com busca (Phase 6). */
export async function listActiveSupplierOptions() {
  const { data } = await http.get<Paginated<Supplier>>('/suppliers', {
    params: { is_active: true, page_size: 100, ordering: 'legal_name' },
  })
  return data.results
}

export async function createSupplier(input: SupplierInput) {
  const { data } = await http.post<Supplier>('/suppliers', input)
  return data
}

export async function updateSupplier(id: string, input: Partial<SupplierInput>) {
  const { data } = await http.patch<Supplier>(`/suppliers/${id}`, input)
  return data
}

export async function setSupplierActive(id: string, active: boolean) {
  const { data } = await http.post<Supplier>(
    `/suppliers/${id}/${active ? 'activate' : 'deactivate'}`,
  )
  return data
}
