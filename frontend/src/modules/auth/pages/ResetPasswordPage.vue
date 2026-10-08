<script setup lang="ts">
import { LinkIcon } from '@lucide/vue'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import FormAlert from '@/components/ui/FormAlert.vue'
import TextField from '@/components/ui/TextField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useZodForm } from '@/composables/useZodForm'
import { confirmPasswordReset } from '@/modules/auth/api/authApi'
import { resetPasswordSchema } from '@/modules/auth/schemas/passwordSchemas'
import { ApiError } from '@/services/http/apiError'

/**
 * Convite aceito ou senha esquecida. O link traz `uid` e `token` no fragmento (#): o navegador não
 * envia fragmento ao servidor. Lido o token, ele sai da barra de endereço e do histórico.
 */
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()

const params = new URLSearchParams(route.hash.replace(/^#/, ''))
const link = { uid: params.get('uid') ?? '', token: params.get('token') ?? '' }
// `replace`: o link com token não fica nem no histórico do navegador.
if (route.hash) void router.replace({ path: route.path, query: route.query, hash: '' })
const invalidLink = ref(!link.uid || !link.token)

const form = useZodForm(resetPasswordSchema, { password: '', confirmation: '' })

async function onSubmit() {
  await form.submit(
    async ({ password }) => {
      await confirmPasswordReset({ ...link, password })
      toasts.success(t('auth.reset.done'))
      await router.replace({ name: 'login' })
    },
    (error) => {
      if (error instanceof ApiError && error.code === 'INVALID_PASSWORD_RESET_TOKEN') {
        invalidLink.value = true
      } else form.formError.value = errorMessage(error)
    },
  )
}
</script>

<template>
  <div class="rounded-lg border border-border bg-surface p-6">
    <h1 class="text-xl font-semibold text-text-primary">{{ t('auth.reset.title') }}</h1>

    <div v-if="invalidLink" class="mt-5 flex flex-col gap-4 text-sm" role="alert">
      <p class="flex items-start gap-2">
        <LinkIcon class="mt-0.5 size-4 shrink-0 text-danger" aria-hidden="true" />
        {{ t('auth.reset.invalidLink') }}
      </p>
      <RouterLink
        :to="{ name: 'forgot-password' }"
        class="text-link underline-offset-2 hover:underline"
      >
        {{ t('auth.reset.askNewLink') }}
      </RouterLink>
    </div>

    <template v-else>
      <p class="mt-1 text-sm text-text-secondary">{{ t('auth.reset.description') }}</p>
      <form class="mt-5 flex flex-col gap-4" novalidate @submit.prevent="onSubmit">
        <FormAlert :message="form.formError.value" />
        <TextField
          v-model="form.values.password"
          type="password"
          :label="t('auth.reset.password')"
          :help="t('auth.reset.passwordHelp')"
          autocomplete="new-password"
          required
          :error="form.errors.value.password"
        />
        <TextField
          v-model="form.values.confirmation"
          type="password"
          :label="t('auth.reset.confirmation')"
          autocomplete="new-password"
          required
          :error="form.errors.value.confirmation"
        />
        <BaseButton type="submit" class="mt-2 w-full" :loading="form.isSubmitting.value">
          {{ t('auth.reset.submit') }}
        </BaseButton>
      </form>
    </template>
  </div>
</template>
