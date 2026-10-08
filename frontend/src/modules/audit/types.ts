export const AUDIT_ACTIONS = [
  'ORDER_CREATED',
  'ORDER_STATUS_CHANGED',
  'ORDER_CANCELLED',
  'PAYMENT_STARTED',
  'PAYMENT_APPROVED',
  'PAYMENT_RECORDED',
  'PAYMENT_DECLINED',
  'PAYMENT_FAILED',
  'PAYMENT_REFUNDED',
  'REFUND_REQUESTED',
  'REFUND_RETRIED',
  'REFUND_COMPLETED',
  'REFUND_FAILED',
  'STOCK_RECEIVED',
  'STOCK_ADJUSTED',
  'STOCK_TRANSFERRED',
  'REORDER_POINT_CHANGED',
] as const
export type AuditAction = (typeof AUDIT_ACTIONS)[number]

export const ENTITY_TYPES = ['ORDER', 'PAYMENT', 'REFUND', 'STOCK_ITEM'] as const
export type EntityType = (typeof ENTITY_TYPES)[number]

export interface AuditLog {
  id: string
  action: AuditAction
  entity_type: EntityType
  entity_id: string
  /** Nome legível guardado no registro ("#000003", "COLA · CD-SP"). */
  entity_label: string
  order_id: string | null
  /** `null` = sistema (jobs, provedor, reconciliação). */
  actor: { id: string; name: string } | null
  reason: string
  /** Campo → [antes, depois], ou valor de contexto (ex.: `amount`). */
  changes: Record<string, unknown>
  occurred_at: string
  request_id: string
}

export interface AuditFilters {
  page: number
  search: string
  action: AuditAction | ''
  entity_type: EntityType | ''
  from: string
  to: string
}
