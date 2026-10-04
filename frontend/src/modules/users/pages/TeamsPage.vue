<script setup lang="ts">
import { CircleSlash, Pencil, Plus, UsersRound } from '@lucide/vue'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import TextField from '@/components/ui/TextField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useZodForm } from '@/composables/useZodForm'
import { useSaveTeam, useTeamsList } from '@/modules/users/composables/useUsers'
import { teamSchema } from '@/modules/users/schemas/userForm'
import type { Team } from '@/modules/users/types'

const { t } = useI18n()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()
const { data, isPending, isError, error, refetch, isFetching } = useTeamsList()
const saveTeam = useSaveTeam()

const dialogOpen = ref(false)
const editing = ref<Team | null>(null)
const form = useZodForm(teamSchema, { name: '' })

function openDialog(team: Team | null) {
  editing.value = team
  form.reset({ name: team?.name ?? '' })
  dialogOpen.value = true
}

async function onSubmit() {
  const saved = await form.submit(
    (data) => saveTeam.mutateAsync({ id: editing.value?.id, name: data.name }),
    (err) => {
      form.formError.value = errorMessage(err)
    },
  )
  if (saved) {
    toasts.success(t(editing.value ? 'teams.feedback.renamed' : 'teams.feedback.created'))
    dialogOpen.value = false
  }
}
</script>

<template>
  <div>
    <PageHeader :title="t('teams.title')" :description="t('teams.description')">
      <template #actions>
        <BaseButton @click="openDialog(null)">
          <Plus class="size-4" aria-hidden="true" />
          {{ t('teams.actions.create') }}
        </BaseButton>
      </template>
    </PageHeader>

    <div
      v-if="isPending"
      class="space-y-2 rounded-lg border border-border bg-surface p-4"
      role="status"
    >
      <span class="sr-only">{{ t('common.loading') }}</span>
      <div v-for="index in 3" :key="index" class="h-9 animate-pulse rounded bg-surface-muted" />
    </div>

    <EmptyState
      v-else-if="isError"
      :title="t('teams.error.title')"
      :description="errorMessage(error)"
      :icon="CircleSlash"
      role="alert"
    >
      <template #action>
        <BaseButton variant="secondary" :loading="isFetching" @click="refetch()">
          {{ t('common.retry') }}
        </BaseButton>
      </template>
    </EmptyState>

    <EmptyState
      v-else-if="data && data.results.length === 0"
      :title="t('teams.empty.title')"
      :description="t('teams.empty.description')"
      :icon="UsersRound"
    >
      <template #action>
        <BaseButton @click="openDialog(null)">{{ t('teams.actions.create') }}</BaseButton>
      </template>
    </EmptyState>

    <ul v-else-if="data" class="divide-y divide-border rounded-lg border border-border bg-surface">
      <li
        v-for="team in data.results"
        :key="team.id"
        class="flex items-center justify-between gap-4 px-4 py-3"
      >
        <div>
          <p class="text-sm font-medium text-text-primary">{{ team.name }}</p>
          <p class="text-xs text-text-secondary">
            {{ t('teams.memberCount', { count: team.member_count }, team.member_count) }}
          </p>
        </div>
        <BaseButton variant="ghost" size="sm" @click="openDialog(team)">
          <Pencil class="size-4" aria-hidden="true" />
          <span class="sr-only">{{ t('teams.actions.renameTeam', { name: team.name }) }}</span>
        </BaseButton>
      </li>
    </ul>

    <BaseDialog
      v-model:open="dialogOpen"
      :title="editing ? t('teams.form.renameTitle') : t('teams.form.createTitle')"
    >
      <form id="team-form" class="flex flex-col gap-4" novalidate @submit.prevent="onSubmit">
        <p v-if="form.formError.value" class="text-sm font-medium text-danger" role="alert">
          {{ form.formError.value }}
        </p>
        <TextField
          v-model="form.values.name"
          :label="t('teams.fields.name')"
          required
          :error="form.errors.value.name"
        />
      </form>
      <template #footer>
        <BaseButton
          variant="secondary"
          :disabled="form.isSubmitting.value"
          @click="dialogOpen = false"
        >
          {{ t('common.cancel') }}
        </BaseButton>
        <BaseButton type="submit" form="team-form" :loading="form.isSubmitting.value">
          {{ t('common.save') }}
        </BaseButton>
      </template>
    </BaseDialog>
  </div>
</template>
