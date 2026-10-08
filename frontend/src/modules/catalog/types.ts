export const UNITS = ['UNIT', 'BOX', 'PACK', 'PAIR'] as const
export type UnitOfMeasure = (typeof UNITS)[number]

export const MAX_CATEGORY_DEPTH = 3

export interface Category {
  id: string
  name: string
  parent_id: string | null
  depth: number
  path: string
  is_active: boolean
}

export interface Product {
  id: string
  sku: string
  name: string
  description: string
  unit: UnitOfMeasure
  barcode: string
  category: { id: string; name: string; path: string; is_active: boolean } | null
  default_supplier: { id: string; display_name: string; is_active: boolean } | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export type StatusFilter = '' | 'active' | 'inactive'

export interface ProductFilters {
  page: number
  search: string
  category: string
  supplier: string
  status: StatusFilter
}

export interface ProductInput {
  sku: string
  name: string
  description: string
  unit: UnitOfMeasure
  barcode: string
  category_id: string | null
  default_supplier_id: string | null
}
