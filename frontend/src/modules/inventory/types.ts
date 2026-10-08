export const MOVEMENT_TYPES = [
  'PURCHASE',
  'RESERVATION',
  'RELEASE',
  'SALE',
  'ADJUSTMENT',
  'RETURN',
  'TRANSFER',
] as const
export type MovementType = (typeof MOVEMENT_TYPES)[number]

/** Saldo de um produto num depósito (informativo; a reserva decide). */
export interface StockAvailability {
  product_id: string
  on_hand: number
  reserved: number
  available: number
}

export interface Warehouse {
  id: string
  code: string
  name: string
  is_active: boolean
  created_at: string
  updated_at: string
}

interface ProductRef {
  id: string
  sku: string
  name: string
  is_active: boolean
}

interface WarehouseRef {
  id: string
  code: string
  name: string
}

export interface StockItem {
  id: string
  product: ProductRef
  warehouse: WarehouseRef
  on_hand: number
  reserved: number
  available: number
  reorder_point: number
  is_low_stock: boolean
  updated_at: string
}

export interface StockMovement {
  id: string
  type: MovementType
  product: ProductRef
  warehouse: WarehouseRef
  on_hand_delta: number
  reserved_delta: number
  on_hand_after: number
  reserved_after: number
  reference_type: string
  reference_id: string | null
  reason: string
  performed_by: { id: string; full_name: string } | null
  created_at: string
}

export interface StockFilters {
  page: number
  search: string
  warehouse: string
  low: '' | 'true'
}

export interface MovementFilters {
  page: number
  search: string
  type: MovementType | ''
  warehouse: string
  product: string
  from: string // YYYY-MM-DD (dia local)
  to: string
}

export interface ReceiptInput {
  warehouse_id: string
  supplier_id: string | null
  document_number: string
  notes: string
  lines: { product_id: string; quantity: number }[]
}
