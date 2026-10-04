<script setup lang="ts">
import { Search } from '@lucide/vue'
import { onBeforeUnmount, ref, useId, watch } from 'vue'

/** Campo de busca com debounce: emite o termo após uma pausa na digitação. */
const model = defineModel<string>({ required: true })
const { label, delay = 300 } = defineProps<{ label: string; delay?: number }>()

const id = useId()
const draft = ref(model.value)
let timer: ReturnType<typeof setTimeout> | undefined

watch(draft, (value) => {
  clearTimeout(timer)
  timer = setTimeout(() => (model.value = value.trim()), delay)
})
// Mudança externa (ex.: voltar no navegador) atualiza o campo.
watch(model, (value) => {
  if (value !== draft.value.trim()) draft.value = value
})
onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <div class="relative min-w-56 flex-1">
    <label :for="id" class="sr-only">{{ label }}</label>
    <Search
      class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-text-secondary"
      aria-hidden="true"
    />
    <input
      :id="id"
      v-model="draft"
      type="search"
      :placeholder="label"
      class="h-9 w-full rounded-md border border-border bg-surface pr-3 pl-9 text-sm text-text-primary placeholder:text-text-secondary"
    />
  </div>
</template>
