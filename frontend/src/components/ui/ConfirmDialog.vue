<script setup lang="ts">
import { CircleAlert } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import BaseButton from '@/components/ui/BaseButton.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'

/**
 * Confirmação de ação destrutiva: texto específico e botão com o verbo da ação.
 * O erro aparece aqui dentro: com o `<dialog>` modal aberto, o resto da página (inclusive os
 * toasts) fica inerte, atrás do backdrop, e não seria visto nem anunciado.
 */
const open = defineModel<boolean>('open', { required: true })
const {
  title,
  description,
  confirmLabel,
  tone = 'danger',
  loading = false,
  error = null,
} = defineProps<{
  title: string
  description: string
  confirmLabel: string
  tone?: 'danger' | 'primary'
  loading?: boolean
  error?: string | null
}>()
const emit = defineEmits<{ confirm: [] }>()

const { t } = useI18n()
</script>

<template>
  <BaseDialog v-model:open="open" :title="title" :description="description">
    <div
      v-if="error"
      class="flex items-start gap-2 rounded-md border border-danger/40 p-3 text-sm"
      role="alert"
    >
      <CircleAlert class="mt-0.5 size-4 shrink-0 text-danger" aria-hidden="true" />
      {{ error }}
    </div>
    <template #footer>
      <BaseButton variant="secondary" :disabled="loading" @click="open = false">
        {{ t('common.cancel') }}
      </BaseButton>
      <BaseButton :variant="tone" :loading="loading" @click="emit('confirm')">
        {{ confirmLabel }}
      </BaseButton>
    </template>
  </BaseDialog>
</template>
