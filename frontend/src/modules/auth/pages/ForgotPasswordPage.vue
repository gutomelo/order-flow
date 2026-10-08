<script setup lang="ts">
import { MailCheck } from '@lucide/vue'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

import BaseButton from '@/components/ui/BaseButton.vue'
import FormAlert from '@/components/ui/FormAlert.vue'
import TextField from '@/components/ui/TextField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useZodForm } from '@/composables/useZodForm'
import { requestPasswordReset } from '@/modules/auth/api/authApi'
import { forgotPasswordSchema } from '@/modules/auth/schemas/passwordSchemas'

const { t } = useI18n()
const errorMessage = useApiErrorMessage()
const form = useZodForm(forgotPasswordSchema, { email: '' })
const sentTo = ref<string | null>(null)

async function onSubmit() {
  await form.submit(
    async ({ email }) => {
      await requestPasswordReset(email)
      sentTo.value = email
    },
    (error) => {
      form.formError.value = errorMessage(error)
    },
  )
}
</script>

<template>
  <div class="rounded-lg border border-border bg-surface p-6">
    <h1 class="text-xl font-semibold text-text-primary">{{ t('auth.forgot.title') }}</h1>

    <!-- Mesma mensagem exista ou não a conta: a tela não revela quais e-mails estão cadastrados. -->
    <div v-if="sentTo" class="mt-5 flex flex-col gap-4 text-sm" role="status">
      <p class="flex items-start gap-2">
        <MailCheck class="mt-0.5 size-4 shrink-0 text-success" aria-hidden="true" />
        {{ t('auth.forgot.sent', { email: sentTo }) }}
      </p>
      <RouterLink :to="{ name: 'login' }" class="text-link underline-offset-2 hover:underline">
        {{ t('auth.backToLogin') }}
      </RouterLink>
    </div>

    <template v-else>
      <p class="mt-1 text-sm text-text-secondary">{{ t('auth.forgot.description') }}</p>
      <form class="mt-5 flex flex-col gap-4" novalidate @submit.prevent="onSubmit">
        <FormAlert :message="form.formError.value" />
        <TextField
          v-model="form.values.email"
          type="email"
          :label="t('auth.login.email')"
          autocomplete="username"
          required
          :error="form.errors.value.email"
        />
        <BaseButton type="submit" class="mt-2 w-full" :loading="form.isSubmitting.value">
          {{ t('auth.forgot.submit') }}
        </BaseButton>
        <RouterLink
          :to="{ name: 'login' }"
          class="text-center text-sm text-link underline-offset-2 hover:underline"
        >
          {{ t('auth.backToLogin') }}
        </RouterLink>
      </form>
    </template>
  </div>
</template>
