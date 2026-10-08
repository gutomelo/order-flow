import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import { formatOrderNumber } from '@/modules/orders/format'
import type { Order } from '@/modules/orders/types'

/** Enviado com reserva → sucesso; enviado sem estoque (ficou Pendente) → aviso, não erro. */
export function useSubmittedNotice() {
  const { t } = useI18n()
  const toasts = useToastStore()
  return (order: Order) => {
    const number = formatOrderNumber(order.number)
    if (order.status === 'PENDING')
      toasts.warning(t('orders.editor.submittedWithoutStock', { number }))
    else toasts.success(t('orders.editor.submitted', { number }))
  }
}
