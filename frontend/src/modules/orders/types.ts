export type OrderStatus =
  | 'DRAFT'
  | 'PENDING'
  | 'AWAITING_PAYMENT'
  | 'PAID'
  | 'PROCESSING'
  | 'READY_TO_SHIP'
  | 'SHIPPED'
  | 'DELIVERED'
  | 'CANCELLED'
  | 'REFUNDED'

export interface OrderCustomer {
  id: string
  display_name: string
  legal_name: string
  tax_id_formatted: string
}

export interface OrderSummary {
  id: string
  number: number | null
  status: OrderStatus
  customer: OrderCustomer
  purchase_order_number: string
  /** Valores monetários são strings decimais ("13.00"). */
  total: string
  currency: string
  lines_count: number
  submitted_at: string | null
  /** Validade da reserva enquanto aguarda pagamento. */
  payment_due_at: string | null
  created_at: string
  updated_at: string
}

export interface OrderLine {
  id: string
  product_id: string
  sku: string
  product_name: string
  quantity: number
  unit_price: string
  discount_amount: string
  line_total: string
  price_source: 'SEGMENT' | 'DEFAULT'
}

export interface OrderHistoryEntry {
  id: string
  from_status: OrderStatus | null
  to_status: OrderStatus
  changed_by: { id: string; name: string } | null
  changed_at: string
  reason: string
}

export interface ShippingAddress {
  address_id: string
  label: string
  postal_code: string
  street: string
  number: string
  complement: string
  district: string
  city: string
  state: string
}

export interface Order extends OrderSummary {
  warehouse: { id: string; code: string; name: string } | null
  shipping_address_id: string | null
  shipping: ShippingAddress | null
  notes: string
  subtotal: string
  discount_total: string
  shipping_total: string
  created_by: { id: string; name: string } | null
  lines: OrderLine[]
  history: OrderHistoryEntry[]
}

export interface OrderFilters {
  page: number
  search: string
  status: OrderStatus | ''
}

export interface LineInput {
  product_id: string
  quantity: number
}

export interface DraftInput {
  customer_id: string
  warehouse_id: string | null
  shipping_address_id: string | null
  purchase_order_number: string
  notes: string
  lines: LineInput[]
}

export interface QuoteLine {
  product_id: string
  sku: string
  product_name: string
  quantity: number
  unit_price: string
  line_total: string
  price_source: 'SEGMENT' | 'DEFAULT'
}

export interface Quote {
  lines: QuoteLine[]
  subtotal: string
  discount_total: string
  shipping_total: string
  total: string
  currency: string
}
