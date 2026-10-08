<script setup lang="ts">
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import FormAlert from '@/components/ui/FormAlert.vue'
import SelectField from '@/components/ui/SelectField.vue'
import TextField from '@/components/ui/TextField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useZodForm } from '@/composables/useZodForm'
import { useSessionStore } from '@/modules/auth/stores/session'
import { ROLES, type Role } from '@/modules/auth/types'
import { useCreateUser, useTeamsList, useUpdateUser } from '@/modules/users/composables/useUsers'
import { ACCESS_MODES, createUserSchema, editUserSchema } from '@/modules/users/schemas/userForm'
import type { User } from '@/modules/users/types'

const open = defineModel<boolean>('open', { required: true })
/**
 * Sem `user`: criação. Com `user`: edição. O pai recria o componente (`:key`) ao trocar de
 * usuário ou de modo, então o schema é escolhido uma vez, no setup.
 */
const { user = null } = defineProps<{ user?: User | null }>()

const { t } = useI18n()
const toasts = useToastStore()
const session = useSessionStore()
const errorMessage = useApiErrorMessage()
const teams = useTeamsList()
const createUser = useCreateUser()
const updateUser = useUpdateUser()

const isEdit = computed(() => user !== null)
// Regra do backend (ninguém altera o próprio papel); aqui só antecipamos o feedback.
const isSelf = computed(() => user !== null && user.id === session.user?.id)

const emptyValues = {
  email: '',
  access: 'invite' as (typeof ACCESS_MODES)[number],
  password: '',
  first_name: '',
  last_name: '',
  role: 'SALES' as Role,
  team_id: '',
}
const initialValues = user
  ? {
      ...emptyValues,
      email: user.email,
      first_name: user.first_name,
      last_name: user.last_name,
      role: user.role,
      team_id: user.team?.id ?? '',
    }
  : emptyValues
const form = useZodForm(user ? editUserSchema : createUserSchema, initialValues)

// Reabrir o mesmo diálogo descarta edições não salvas.
watch(open, (isOpen) => {
  if (isOpen) form.reset(initialValues)
})

const roleOptions = computed(() =>
  ROLES.map((role) => ({ value: role, label: t(`roles.${role}`) })),
)
const accessOptions = computed(() =>
  ACCESS_MODES.map((value) => ({ value, label: t(`users.form.access.${value}`) })),
)
const teamOptions = computed(() => [
  { value: '', label: t('users.form.noTeam') },
  ...(teams.data.value?.results ?? []).map((team) => ({ value: team.id, label: team.name })),
])

async function onSubmit() {
  const saved = await form.submit(
    async (data) => {
      const teamId = data.team_id || null
      if (user) {
        await updateUser.mutateAsync({
          id: user.id,
          profile: { first_name: data.first_name, last_name: data.last_name, team_id: teamId },
          role: isSelf.value ? undefined : data.role,
        })
      } else {
        await createUser.mutateAsync({
          email: data.email,
          first_name: data.first_name,
          last_name: data.last_name,
          role: data.role,
          team_id: teamId,
          password: data.access === 'password' ? data.password : null,
        })
      }
    },
    (error) => {
      form.formError.value = errorMessage(error)
    },
  )
  // No convite o campo de senha não aparece: um erro nele precisa ir para o topo, senão some.
  const hiddenPasswordError = form.values.access === 'invite' && form.errors.value.password
  if (hiddenPasswordError) form.formError.value = hiddenPasswordError
  if (saved) {
    toasts.success(
      isEdit.value
        ? t('users.feedback.updated')
        : form.values.access === 'invite'
          ? t('users.feedback.invited', { email: form.values.email })
          : t('users.feedback.created'),
    )
    open.value = false
  }
}
</script>

<template>
  <BaseDialog
    v-model:open="open"
    :title="isEdit ? t('users.form.editTitle') : t('users.form.createTitle')"
    :description="isEdit ? user?.email : t('users.form.createDescription')"
  >
    <form id="user-form" class="flex flex-col gap-4" novalidate @submit.prevent="onSubmit">
      <FormAlert :message="form.formError.value" />

      <div class="grid gap-4 sm:grid-cols-2">
        <TextField
          v-model="form.values.first_name"
          :label="t('users.fields.firstName')"
          autocomplete="off"
          required
          :error="form.errors.value.first_name"
        />
        <TextField
          v-model="form.values.last_name"
          :label="t('users.fields.lastName')"
          autocomplete="off"
          :error="form.errors.value.last_name"
        />
      </div>

      <template v-if="!isEdit">
        <TextField
          v-model="form.values.email"
          type="email"
          :label="t('users.fields.email')"
          autocomplete="off"
          required
          :error="form.errors.value.email"
        />
        <SelectField
          v-model="form.values.access"
          :label="t('users.form.access.label')"
          :options="accessOptions"
          :help="form.values.access === 'invite' ? t('users.form.access.inviteHelp') : undefined"
        />
        <TextField
          v-if="form.values.access === 'password'"
          v-model="form.values.password"
          type="password"
          :label="t('users.fields.initialPassword')"
          autocomplete="new-password"
          required
          :help="t('users.form.passwordHelp')"
          :error="form.errors.value.password"
        />
      </template>

      <div class="grid gap-4 sm:grid-cols-2">
        <SelectField
          v-model="form.values.role"
          :label="t('users.fields.role')"
          :options="roleOptions"
          required
          :help="isSelf ? t('users.form.selfRoleHelp') : undefined"
          :error="form.errors.value.role"
          :disabled="isSelf"
        />
        <SelectField
          v-model="form.values.team_id"
          :label="t('users.fields.team')"
          :options="teamOptions"
          :error="form.errors.value.team_id"
        />
      </div>
    </form>

    <template #footer>
      <BaseButton variant="secondary" :disabled="form.isSubmitting.value" @click="open = false">
        {{ t('common.cancel') }}
      </BaseButton>
      <BaseButton type="submit" form="user-form" :loading="form.isSubmitting.value">
        {{ isEdit ? t('common.save') : t('users.actions.create') }}
      </BaseButton>
    </template>
  </BaseDialog>
</template>
