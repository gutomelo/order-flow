import type { SegmentSummary } from '@/modules/customers/types'

export interface PriceList {
  id: string
  name: string
  segment: SegmentSummary | null
  is_default: boolean
  currency: string
  items_count: number
  created_at: string
  updated_at: string
}

export interface PriceListItem {
  id: string
  product: { id: string; sku: string; name: string; is_active: boolean }
  /** String decimal ("3.50"). */
  unit_price: string
  created_at: string
  updated_at: string
}

export interface PriceItemFilters {
  page: number
  search: string
}
