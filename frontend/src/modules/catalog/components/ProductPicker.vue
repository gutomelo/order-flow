<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import SearchCombobox from '@/components/ui/SearchCombobox.vue'
import { searchActiveProducts } from '@/modules/catalog/api/catalogApi'

export interface ProductOption {
  id: string
  sku: string
  name: string
}

/** Seletor de produto ativo com busca por nome, SKU ou código de barras. */
const model = defineModel<ProductOption | null>({ required: true })
const {
  label,
  error,
  excludeIds = [],
  hideLabel = false,
} = defineProps<{ label: string; error?: string; excludeIds?: string[]; hideLabel?: boolean }>()

const { t } = useI18n()

const search = async (term: string): Promise<ProductOption[]> =>
  (await searchActiveProducts(term)).map(({ id, sku, name }) => ({ id, sku, name }))
</script>

<template>
  <SearchCombobox
    v-model="model"
    :label="label"
    :query-key="['products', 'search']"
    :search="search"
    :display="(option) => `${option.sku} — ${option.name}`"
    :error="error"
    :placeholder="t('catalog.picker.placeholder')"
    :empty-text="t('catalog.picker.empty')"
    :toggle-label="t('catalog.picker.showOptions')"
    :exclude-ids="excludeIds"
    :hide-label="hideLabel"
  >
    <template #option="{ option }">
      <span class="font-mono text-xs text-text-secondary">{{ option.sku }}</span>
      <span class="truncate">{{ option.name }}</span>
    </template>
  </SearchCombobox>
</template>
