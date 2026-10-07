<script setup lang="ts">
import { PackageCheck, PackageOpen, Truck, CircleCheck } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import FormAlert from '@/components/ui/FormAlert.vue'
import TextAreaField from '@/components/ui/TextAreaField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useSessionStore } from '@/modules/auth/stores/session'
import { useAdvanceFulfillment, useConfirmDelivery } from '@/modules/orders/composables/useOrders'
import { formatOrderNumber } from '@/modules/orders/format'
import { NEXT_FULFILLMENT_ACTION } from '@/modules/orders/fulfillment'
import type { OrderSummary } from '@/modules/orders/types'

/**
 * Próximo passo da expedição de um pedido (detalhe e fila da expedição). Separação é um clique;
 * despachar e confirmar entrega pedem confirmação (o despacho não pode ser desfeito).
 */
const { order, size = 'md' } = defineProps<{ order: OrderSummary; size?: 'sm' | 'md' }>()

const { t } = useI18n()
const session = useSessionStore()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()

const next = computed(() => {
  const step = NEXT_FULFILLMENT_ACTION[order.status]
  return step && session.can(step.permission) ? step.action : null
})
const icons = {
  'start-picking': PackageOpen,
  'complete-picking': PackageCheck,
  ship: Truck,
  'confirm-delivery': CircleCheck,
}
const number = computed(() => formatOrderNumber(order.number))

const advance = useAdvanceFulfillment()
const deliver = useConfirmDelivery()
const dialogOpen = ref(false)
const dialogError = ref<string | null>(null)
const note = ref('')

async function onClick() {
  if (next.value === 'ship' || next.value === 'confirm-delivery') {
    dialogError.value = null
    note.value = ''
    dialogOpen.value = true
    return
  }
  if (!next.value) return
  const step = next.value
  try {
    await advance.mutateAsync({ id: order.id, step })
    toasts.success(t(`orders.fulfillment.done.${step}`, { number: number.value }))
  } catch (cause) {
    toasts.error(errorMessage(cause))
  }
}

async function onShip() {
  dialogError.value = null
  try {
    await advance.mutateAsync({ id: order.id, step: 'ship' })
    dialogOpen.value = false
    toasts.success(t('orders.fulfillment.done.ship', { number: number.value }))
  } catch (cause) {
    dialogError.value = errorMessage(cause)
  }
}

async function onDeliver() {
  dialogError.value = null
  try {
    await deliver.mutateAsync({ id: order.id, note: note.value.trim() })
    dialogOpen.value = false
    toasts.success(t('orders.fulfillment.done.confirm-delivery', { number: number.value }))
  } catch (cause) {
    dialogError.value = errorMessage(cause)
  }
}
</script>

<template>
  <template v-if="next">
    <BaseButton
      :size="size"
      :variant="next === 'confirm-delivery' ? 'secondary' : 'primary'"
      :loading="advance.isPending.value && !dialogOpen"
      @click="onClick"
    >
      <component :is="icons[next]" class="size-4" aria-hidden="true" />
      {{ t(`orders.fulfillment.actions.${next}`) }}
      <!-- Na fila há um botão igual por linha: o número do pedido distingue para leitores de tela. -->
      <span class="sr-only">{{ ` ${t('orders.fulfillment.ofOrder', { number })}` }}</span>
    </BaseButton>

    <ConfirmDialog
      v-if="next === 'ship'"
      v-model:open="dialogOpen"
      tone="primary"
      :title="t('orders.fulfillment.shipDialog.title', { number })"
      :description="t('orders.fulfillment.shipDialog.description')"
      :confirm-label="t('orders.fulfillment.actions.ship')"
      :loading="advance.isPending.value"
      :error="dialogError"
      @confirm="onShip"
    />

    <BaseDialog
      v-if="next === 'confirm-delivery'"
      v-model:open="dialogOpen"
      :title="t('orders.fulfillment.deliveryDialog.title', { number })"
      :description="t('orders.fulfillment.deliveryDialog.description')"
    >
      <form
        :id="`deliver-${order.id}`"
        class="flex flex-col gap-4"
        novalidate
        @submit.prevent="onDeliver"
      >
        <FormAlert :message="dialogError" />
        <TextAreaField
          v-model="note"
          :label="t('orders.fulfillment.deliveryDialog.note')"
          :help="t('orders.fulfillment.deliveryDialog.noteHelp')"
          :rows="2"
        />
      </form>
      <template #footer>
        <BaseButton
          variant="secondary"
          :disabled="deliver.isPending.value"
          @click="dialogOpen = false"
        >
          {{ t('common.cancel') }}
        </BaseButton>
        <BaseButton type="submit" :form="`deliver-${order.id}`" :loading="deliver.isPending.value">
          {{ t('orders.fulfillment.actions.confirm-delivery') }}
        </BaseButton>
      </template>
    </BaseDialog>
  </template>
</template>
