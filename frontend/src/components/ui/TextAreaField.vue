<script setup lang="ts">
import { useId } from 'vue'

const model = defineModel<string>({ required: true })
const {
  label,
  error,
  help,
  rows = 3,
} = defineProps<{
  label: string
  error?: string
  help?: string
  rows?: number
}>()

const id = useId()
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <label :for="id" class="text-sm font-medium text-text-primary">{{ label }}</label>
    <textarea
      :id="id"
      v-model="model"
      :rows="rows"
      :aria-invalid="error ? true : undefined"
      :aria-describedby="error ? `${id}-error` : help ? `${id}-help` : undefined"
      class="rounded-md border bg-surface px-3 py-2 text-sm text-text-primary"
      :class="error ? 'border-danger' : 'border-border'"
    />
    <p v-if="help && !error" :id="`${id}-help`" class="text-xs text-text-secondary">{{ help }}</p>
    <p v-if="error" :id="`${id}-error`" class="text-xs font-medium text-danger">{{ error }}</p>
  </div>
</template>
