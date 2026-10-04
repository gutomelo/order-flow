<script setup lang="ts">
import { CircleAlert } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import BaseButton from '@/components/ui/BaseButton.vue'
import TextField from '@/components/ui/TextField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useZodForm } from '@/composables/useZodForm'
import { loginSchema } from '@/modules/auth/schemas/loginSchema'
import { useSessionStore } from '@/modules/auth/stores/session'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const errorMessage = useApiErrorMessage()

const form = useZodForm(loginSchema, { email: '', password: '' })

// Só aceita redirecionar para caminhos internos (evita open redirect via ?redirect=).
function safeRedirect(value: unknown): string {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//')
    ? value
    : '/dashboard'
}

async function onSubmit() {
  await form.submit(
    async ({ email, password }) => {
      await session.login(email, password)
      await router.replace(safeRedirect(route.query.redirect))
    },
    (error) => {
      form.formError.value = errorMessage(error)
    },
  )
}
</script>

<template>
  <div class="rounded-lg border border-border bg-surface p-6">
    <h1 class="text-xl font-semibold text-text-primary">{{ t('auth.login.title') }}</h1>
    <p class="mt-1 text-sm text-text-secondary">{{ t('auth.login.description') }}</p>

    <div
      v-if="form.formError.value"
      class="mt-5 flex items-start gap-2 rounded-md border border-danger/40 p-3 text-sm text-text-primary"
      role="alert"
    >
      <CircleAlert class="mt-0.5 size-4 shrink-0 text-danger" aria-hidden="true" />
      {{ form.formError.value }}
    </div>

    <form class="mt-5 flex flex-col gap-4" novalidate @submit.prevent="onSubmit">
      <TextField
        v-model="form.values.email"
        type="email"
        :label="t('auth.login.email')"
        autocomplete="username"
        required
        :error="form.errors.value.email"
      />
      <TextField
        v-model="form.values.password"
        type="password"
        :label="t('auth.login.password')"
        autocomplete="current-password"
        required
        :error="form.errors.value.password"
      />
      <BaseButton type="submit" class="mt-2 w-full" :loading="form.isSubmitting.value">
        {{ t('auth.login.submit') }}
      </BaseButton>
    </form>
  </div>
</template>
