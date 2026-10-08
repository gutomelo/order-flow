export interface SegmentSummary {
  id: string
  code: string
  name: string
  is_active: boolean
}

export interface Segment extends SegmentSummary {
  description: string
  active_customers: number
  created_at: string
  updated_at: string
}

export interface Customer {
  id: string
  legal_name: string
  trade_name: string
  display_name: string
  tax_id: string
  tax_id_formatted: string
  email: string
  phone: string
  segment: SegmentSummary | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CustomerAddress {
  id: string
  label: string
  postal_code: string
  street: string
  number: string
  complement: string
  district: string
  city: string
  state: string
  is_billing: boolean
  is_default_shipping: boolean
  created_at: string
  updated_at: string
}

export interface CustomerContact {
  id: string
  name: string
  job_title: string
  email: string
  phone: string
  is_primary: boolean
  created_at: string
  updated_at: string
}

export type StatusFilter = '' | 'active' | 'inactive'

export interface CustomerFilters {
  page: number
  search: string
  status: StatusFilter
  segment: string
}

export interface SegmentFilters {
  page: number
  search: string
  status: StatusFilter
}

export interface CustomerInput {
  legal_name: string
  trade_name: string
  tax_id: string
  email: string
  phone: string
  segment_id: string | null
}

export interface SegmentInput {
  code: string
  name: string
  description: string
}

export interface AddressInput {
  label: string
  postal_code: string
  street: string
  number: string
  complement: string
  district: string
  city: string
  state: string
}

export interface ContactInput {
  name: string
  job_title: string
  email: string
  phone: string
}

export type AddressRole = 'billing' | 'default-shipping'
