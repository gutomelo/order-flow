<script setup lang="ts" generic="T extends { id: string }">
import { Check, ChevronsUpDown } from '@lucide/vue'
import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import {
  ComboboxAnchor,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxItemIndicator,
  ComboboxRoot,
  ComboboxTrigger,
  ComboboxViewport,
} from 'reka-ui'
import { computed, onBeforeUnmount, ref, useId, watch } from 'vue'
import { useI18n } from 'vue-i18n'

/**
 * Combobox com busca no servidor (debounce de 250 ms).
 *
 * Reka UI fornece o padrão ARIA de combobox (teclado, leitores de tela). A lista NÃO usa
 * portal: dentro de um <dialog> modal o restante da página é inerte e um portal no <body>
 * ficaria inacessível.
 */
const model = defineModel<T | null>({ required: true })
const {
  label,
  queryKey,
  search,
  display,
  error,
  placeholder,
  emptyText,
  toggleLabel,
  excludeIds = [],
  hideLabel = false,
} = defineProps<{
  label: string
  /** Prefixo da chave de cache; o termo buscado é acrescentado. */
  queryKey: readonly unknown[]
  search: (term: string) => Promise<T[]>
  /** Texto exibido no campo para a opção escolhida. */
  display: (option: T) => string
  error?: string
  placeholder: string
  emptyText: string
  /** Nome acessível do botão que abre a lista (ex.: "Mostrar produtos"). */
  toggleLabel: string
  excludeIds?: string[]
  hideLabel?: boolean
}>()

defineSlots<{ option(props: { option: T }): unknown }>()

const { t } = useI18n()
const id = useId()

const searchTerm = ref('')
const debouncedTerm = ref('')
let timer: ReturnType<typeof setTimeout> | undefined
watch(searchTerm, (value) => {
  clearTimeout(timer)
  timer = setTimeout(() => (debouncedTerm.value = value.trim()), 250)
})
onBeforeUnmount(() => clearTimeout(timer))

const { data, isFetching } = useQuery({
  queryKey: computed(() => [...queryKey, debouncedTerm.value]),
  queryFn: () => search(debouncedTerm.value),
  placeholderData: keepPreviousData,
  staleTime: 30_000,
})

const options = computed<T[]>(() =>
  (data.value ?? []).filter(
    (option) => !excludeIds.includes(option.id) || option.id === model.value?.id,
  ),
)

const displayValue = (option: T | null | undefined) => (option ? display(option) : '')
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <label
      :for="id"
      class="text-sm font-medium text-text-primary"
      :class="{ 'sr-only': hideLabel }"
    >
      {{ label }}
    </label>
    <ComboboxRoot
      v-model="model"
      by="id"
      :ignore-filter="true"
      :open-on-focus="true"
      class="relative"
    >
      <ComboboxAnchor
        class="flex h-9 items-center rounded-md border bg-surface pr-1 text-sm"
        :class="error ? 'border-danger' : 'border-border'"
      >
        <ComboboxInput
          :id="id"
          v-model="searchTerm"
          :display-value="displayValue"
          :placeholder="placeholder"
          :aria-invalid="error ? true : undefined"
          :aria-describedby="error ? `${id}-error` : undefined"
          class="h-full min-w-0 flex-1 bg-transparent px-3 text-text-primary placeholder:text-text-secondary focus:outline-none"
        />
        <ComboboxTrigger
          class="inline-flex size-7 items-center justify-center rounded text-text-secondary hover:bg-surface-muted"
          :aria-label="toggleLabel"
        >
          <ChevronsUpDown class="size-4" aria-hidden="true" />
        </ComboboxTrigger>
      </ComboboxAnchor>

      <ComboboxContent
        class="absolute z-50 mt-1 max-h-64 w-full overflow-hidden rounded-md border border-border bg-surface shadow-lg"
      >
        <ComboboxViewport class="max-h-64 overflow-y-auto p-1">
          <ComboboxEmpty class="px-3 py-2 text-sm text-text-secondary">
            {{ isFetching ? t('common.loading') : emptyText }}
          </ComboboxEmpty>
          <ComboboxItem
            v-for="option in options"
            :key="option.id"
            :value="option"
            class="relative flex cursor-default items-center gap-2 rounded px-3 py-2 pr-8 text-sm text-text-primary select-none data-[highlighted]:bg-surface-muted"
          >
            <slot name="option" :option="option">{{ display(option) }}</slot>
            <ComboboxItemIndicator class="absolute right-2">
              <Check class="size-4 text-primary" aria-hidden="true" />
            </ComboboxItemIndicator>
          </ComboboxItem>
        </ComboboxViewport>
      </ComboboxContent>
    </ComboboxRoot>
    <p v-if="error" :id="`${id}-error`" class="text-xs font-medium text-danger">{{ error }}</p>
  </div>
</template>
