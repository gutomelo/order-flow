<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import BaseButton from '@/components/ui/BaseButton.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'

/** Confirmação de ação destrutiva: texto específico e botão com o verbo da ação. */
const open = defineModel<boolean>('open', { required: true })
const {
  title,
  description,
  confirmLabel,
  tone = 'danger',
  loading = false,
} = defineProps<{
  title: string
  description: string
  confirmLabel: string
  tone?: 'danger' | 'primary'
  loading?: boolean
}>()
const emit = defineEmits<{ confirm: [] }>()

const { t } = useI18n()
</script>

<template>
  <BaseDialog v-model:open="open" :title="title" :description="description">
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
