import type {
  AddressInput,
  AddressRole,
  ContactInput,
  Customer,
  CustomerAddress,
  CustomerContact,
  CustomerFilters,
  CustomerInput,
  Segment,
  SegmentFilters,
  SegmentInput,
} from '@/modules/customers/types'
import { http } from '@/services/http/client'
import type { Paginated } from '@/types/api'

export const CUSTOMERS_PAGE_SIZE = 25
export const SEGMENTS_PAGE_SIZE = 25

// Clientes -------------------------------------------------------------------------------------

export async function listCustomers(filters: CustomerFilters) {
  const params: Record<string, string | number | boolean> = {
    page: filters.page,
    page_size: CUSTOMERS_PAGE_SIZE,
  }
  if (filters.search) params.search = filters.search
  if (filters.status) params.is_active = filters.status === 'active'
  if (filters.segment) params.segment = filters.segment
  const { data } = await http.get<Paginated<Customer>>('/customers', { params })
  return data
}

/** Clientes ativos para seletores com busca (pedidos). */
export async function searchActiveCustomers(term: string) {
  const { data } = await http.get<Paginated<Customer>>('/customers', {
    params: { search: term, is_active: true, page_size: 20, ordering: 'legal_name' },
  })
  return data.results
}

export async function getCustomer(id: string) {
  const { data } = await http.get<Customer>(`/customers/${id}`)
  return data
}

export async function createCustomer(input: CustomerInput) {
  const { data } = await http.post<Customer>('/customers', input)
  return data
}

export async function updateCustomer(id: string, input: Partial<CustomerInput>) {
  const { data } = await http.patch<Customer>(`/customers/${id}`, input)
  return data
}

export async function setCustomerActive(id: string, active: boolean) {
  const { data } = await http.post<Customer>(
    `/customers/${id}/${active ? 'activate' : 'deactivate'}`,
  )
  return data
}

// Segmentos ------------------------------------------------------------------------------------

export async function listSegments(filters: SegmentFilters) {
  const params: Record<string, string | number | boolean> = {
    page: filters.page,
    page_size: SEGMENTS_PAGE_SIZE,
  }
  if (filters.search) params.search = filters.search
  if (filters.status) params.is_active = filters.status === 'active'
  const { data } = await http.get<Paginated<Segment>>('/customer-segments', { params })
  return data
}

/** Todos os segmentos para seletores e filtros (poucos por organização; limite de 100). */
export async function listSegmentOptions() {
  const { data } = await http.get<Paginated<Segment>>('/customer-segments', {
    params: { page_size: 100, ordering: 'name' },
  })
  return data.results
}

export async function createSegment(input: SegmentInput) {
  const { data } = await http.post<Segment>('/customer-segments', input)
  return data
}

export async function updateSegment(id: string, input: Omit<SegmentInput, 'code'>) {
  const { data } = await http.patch<Segment>(`/customer-segments/${id}`, input)
  return data
}

export async function setSegmentActive(id: string, active: boolean) {
  const { data } = await http.post<Segment>(
    `/customer-segments/${id}/${active ? 'activate' : 'deactivate'}`,
  )
  return data
}

// Endereços e contatos -------------------------------------------------------------------------

export async function listAddresses(customerId: string) {
  const { data } = await http.get<CustomerAddress[]>(`/customers/${customerId}/addresses`)
  return data
}

export async function saveAddress(customerId: string, input: AddressInput, id?: string) {
  const base = `/customers/${customerId}/addresses`
  const { data } = id
    ? await http.patch<CustomerAddress>(`${base}/${id}`, input)
    : await http.post<CustomerAddress>(base, input)
  return data
}

export async function setAddressRole(customerId: string, id: string, role: AddressRole) {
  const { data } = await http.post<CustomerAddress>(
    `/customers/${customerId}/addresses/${id}/set-${role}`,
  )
  return data
}

export async function removeAddress(customerId: string, id: string) {
  await http.delete(`/customers/${customerId}/addresses/${id}`)
}

export async function listContacts(customerId: string) {
  const { data } = await http.get<CustomerContact[]>(`/customers/${customerId}/contacts`)
  return data
}

export async function saveContact(customerId: string, input: ContactInput, id?: string) {
  const base = `/customers/${customerId}/contacts`
  const { data } = id
    ? await http.patch<CustomerContact>(`${base}/${id}`, input)
    : await http.post<CustomerContact>(base, input)
  return data
}

export async function setPrimaryContact(customerId: string, id: string) {
  const { data } = await http.post<CustomerContact>(
    `/customers/${customerId}/contacts/${id}/set-primary`,
  )
  return data
}

export async function removeContact(customerId: string, id: string) {
  await http.delete(`/customers/${customerId}/contacts/${id}`)
}
