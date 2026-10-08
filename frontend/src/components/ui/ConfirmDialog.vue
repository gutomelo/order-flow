<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import BaseButton from '@/components/ui/BaseButton.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import FormAlert from '@/components/ui/FormAlert.vue'

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
    <FormAlert :message="error" />
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
