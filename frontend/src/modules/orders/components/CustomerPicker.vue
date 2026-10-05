<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import SearchCombobox from '@/components/ui/SearchCombobox.vue'
import { searchActiveCustomers } from '@/modules/customers/api/customersApi'

export interface CustomerOption {
  id: string
  display_name: string
  tax_id_formatted: string
}

/** Seletor de cliente ativo com busca por nome, CNPJ ou e-mail. */
const model = defineModel<CustomerOption | null>({ required: true })
const { label, error } = defineProps<{ label: string; error?: string }>()

const { t } = useI18n()

const search = async (term: string): Promise<CustomerOption[]> =>
  (await searchActiveCustomers(term)).map(({ id, display_name, tax_id_formatted }) => ({
    id,
    display_name,
    tax_id_formatted,
  }))
</script>

<template>
  <SearchCombobox
    v-model="model"
    :label="label"
    :query-key="['customers', 'search']"
    :search="search"
    :display="(option) => `${option.display_name} — ${option.tax_id_formatted}`"
    :error="error"
    :placeholder="t('orders.editor.customerPlaceholder')"
    :empty-text="t('orders.editor.customerEmpty')"
    :toggle-label="t('orders.editor.showCustomers')"
  >
    <template #option="{ option }">
      <span class="truncate">{{ option.display_name }}</span>
      <span class="text-xs text-text-secondary tabular-nums">{{ option.tax_id_formatted }}</span>
    </template>
  </SearchCombobox>
</template>
