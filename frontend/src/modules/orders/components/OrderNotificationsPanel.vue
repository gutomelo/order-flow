<script setup lang="ts">
import { CircleCheck, CircleSlash, Hourglass, TriangleAlert } from '@lucide/vue'
import type { Component } from 'vue'
import { useI18n } from 'vue-i18n'

import StatusBadge from '@/components/ui/StatusBadge.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useOrderNotifications } from '@/modules/orders/composables/useOrders'
import type { NotificationStatus, Order } from '@/modules/orders/types'
import { formatDateTime } from '@/utils/datetime'

/** O que o cliente recebeu por e-mail sobre este pedido (e o que não pôde ser enviado). */
const { order } = defineProps<{ order: Order }>()
const { t, te } = useI18n()
const errorMessage = useApiErrorMessage()
const { data, isPending, error } = useOrderNotifications(() => order)

type Tone = 'success' | 'danger' | 'warning' | 'neutral'
const appearance: Record<NotificationStatus, { icon: Component; tone: Tone }> = {
  PENDING: { icon: Hourglass, tone: 'warning' },
  SENT: { icon: CircleCheck, tone: 'success' },
  FAILED: { icon: TriangleAlert, tone: 'danger' },
  SKIPPED: { icon: CircleSlash, tone: 'neutral' },
}
const kindLabel = (kind: string) =>
  te(`orders.notifications.kinds.${kind}`) ? t(`orders.notifications.kinds.${kind}`) : kind
</script>

<template>
  <section
    aria-labelledby="order-notifications-heading"
    class="rounded-lg border border-border bg-surface p-5 text-sm"
  >
    <h2 id="order-notifications-heading" class="mb-3 text-base font-semibold">
      {{ t('orders.notifications.title') }}
    </h2>
    <p v-if="isPending" class="text-text-secondary" role="status">{{ t('common.loading') }}</p>
    <p v-else-if="error" class="text-danger" role="alert">{{ errorMessage(error) }}</p>
    <p v-else-if="!data?.length" class="text-text-secondary">
      {{ t('orders.notifications.empty') }}
    </p>
    <ul v-else class="flex flex-col gap-3">
      <li
        v-for="notification in data"
        :key="notification.id"
        class="flex flex-wrap items-start justify-between gap-2"
      >
        <div class="min-w-0">
          <p class="font-medium">{{ kindLabel(notification.kind) }}</p>
          <p class="text-xs text-text-secondary">
            {{
              notification.recipient
                ? t('orders.notifications.to', { recipient: notification.recipient })
                : t('orders.notifications.noRecipient')
            }}
            · {{ formatDateTime(notification.sent_at ?? notification.created_at) }}
          </p>
        </div>
        <StatusBadge
          :label="t(`orders.notifications.status.${notification.status}`)"
          :icon="appearance[notification.status].icon"
          :tone="appearance[notification.status].tone"
        />
      </li>
    </ul>
  </section>
</template>
