<script setup lang="ts">
import { useId } from 'vue'

// <select> nativo: acessível por padrão (teclado, leitores de tela, mobile).
const model = defineModel<string>({ required: true })

const {
  label,
  options,
  error,
  help,
  required = false,
  hideLabel = false,
  disabled = false,
} = defineProps<{
  label: string
  options: { value: string; label: string }[]
  error?: string
  help?: string
  required?: boolean
  hideLabel?: boolean
  disabled?: boolean
}>()

const id = useId()
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <label
      :for="id"
      class="text-sm font-medium text-text-primary"
      :class="{ 'sr-only': hideLabel }"
    >
      {{ label }}<span v-if="required" class="text-danger" aria-hidden="true"> *</span>
    </label>
    <select
      :id="id"
      v-model="model"
      :required="required"
      :disabled="disabled"
      :aria-invalid="error ? true : undefined"
      :aria-describedby="error ? `${id}-error` : help ? `${id}-help` : undefined"
      class="h-9 rounded-md border bg-surface px-3 text-sm text-text-primary disabled:cursor-not-allowed disabled:opacity-60"
      :class="error ? 'border-danger' : 'border-border'"
    >
      <option v-for="option in options" :key="option.value" :value="option.value">
        {{ option.label }}
      </option>
    </select>
    <p v-if="help && !error" :id="`${id}-help`" class="text-xs text-text-secondary">{{ help }}</p>
    <p v-if="error" :id="`${id}-error`" class="text-xs font-medium text-danger">{{ error }}</p>
  </div>
</template>
