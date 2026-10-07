import type { OrderStatus } from '@/modules/orders/types'

export type FulfillmentAction = 'start-picking' | 'complete-picking' | 'ship' | 'confirm-delivery'

/**
 * Próximo passo da expedição por status (espelha a máquina de estados do backend, que decide;
 * aqui é só para mostrar o botão certo a quem tem a permissão).
 */
export const NEXT_FULFILLMENT_ACTION: Partial<
  Record<OrderStatus, { action: FulfillmentAction; permission: string }>
> = {
  PAID: { action: 'start-picking', permission: 'orders:process' },
  PROCESSING: { action: 'complete-picking', permission: 'orders:process' },
  READY_TO_SHIP: { action: 'ship', permission: 'orders:ship' },
  SHIPPED: { action: 'confirm-delivery', permission: 'orders:ship' },
}

/** Etapas mostradas no pedido, na ordem: concluída quando o pedido já passou dela. */
export const FULFILLMENT_STEPS: OrderStatus[] = [
  'PROCESSING',
  'READY_TO_SHIP',
  'SHIPPED',
  'DELIVERED',
]
