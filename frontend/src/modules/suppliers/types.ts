export interface Supplier {
  id: string
  legal_name: string
  trade_name: string
  display_name: string
  tax_id: string
  tax_id_formatted: string
  email: string
  phone: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export type StatusFilter = '' | 'active' | 'inactive'

export interface SupplierFilters {
  page: number
  search: string
  status: StatusFilter
}

export interface SupplierInput {
  legal_name: string
  trade_name: string
  tax_id: string
  email: string
  phone: string
}
