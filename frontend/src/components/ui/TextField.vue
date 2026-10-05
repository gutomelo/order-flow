<script setup lang="ts">
import { useId } from 'vue'

const model = defineModel<string>({ required: true })

const {
  label,
  type = 'text',
  error,
  help,
  required = false,
  autocomplete,
  placeholder,
  inputmode,
  hideLabel = false,
} = defineProps<{
  label: string
  type?: 'text' | 'email' | 'password' | 'search'
  error?: string
  help?: string
  required?: boolean
  autocomplete?: string
  placeholder?: string
  inputmode?: 'numeric' | 'decimal' | 'text'
  hideLabel?: boolean
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
    <input
      :id="id"
      v-model="model"
      :type="type"
      :required="required"
      :autocomplete="autocomplete"
      :placeholder="placeholder"
      :inputmode="inputmode"
      :aria-invalid="error ? true : undefined"
      :aria-describedby="
        [error ? `${id}-error` : '', help ? `${id}-help` : ''].join(' ').trim() || undefined
      "
      class="h-9 rounded-md border bg-surface px-3 text-sm text-text-primary placeholder:text-text-secondary"
      :class="error ? 'border-danger' : 'border-border'"
    />
    <p v-if="help && !error" :id="`${id}-help`" class="text-xs text-text-secondary">{{ help }}</p>
    <p v-if="error" :id="`${id}-error`" class="text-xs font-medium text-danger">{{ error }}</p>
  </div>
</template>
