<script setup lang="ts">
import { CircleAlert, CircleCheck, CircleX, RefreshCw } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useSystemHealth } from '@/modules/dashboard/composables/useSystemHealth'
import { ApiError } from '@/services/http/apiError'
import { formatTime } from '@/utils/datetime'

const { t } = useI18n()
const errorMessage = useApiErrorMessage()
const { data, error, isPending, isError, isFetching, dataUpdatedAt, refetch } = useSystemHealth()

const checks = computed(() => Object.entries(data.value?.checks ?? {}))
const healthy = computed(() => data.value?.status === 'ok')
const requestId = computed(() => (error.value instanceof ApiError ? error.value.requestId : null))
</script>

<template>
  <section
    class="rounded-lg border border-border bg-surface p-5"
    aria-labelledby="system-health-title"
    :aria-busy="isFetching"
  >
    <div class="flex items-start justify-between gap-4">
      <div>
        <h2 id="system-health-title" class="text-base font-semibold text-text-primary">
          {{ t('dashboard.health.title') }}
        </h2>
        <p class="mt-1 text-sm text-text-secondary">{{ t('dashboard.health.description') }}</p>
      </div>
      <button
        type="button"
        class="inline-flex h-8 shrink-0 items-center gap-2 rounded-md whitespace-nowrap border border-border px-3 text-sm font-medium text-text-primary hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="isFetching"
        @click="refetch()"
      >
        <RefreshCw class="size-4" :class="{ 'animate-spin': isFetching }" aria-hidden="true" />
        {{ t('dashboard.health.refresh') }}
      </button>
    </div>

    <!-- Loading -->
    <div v-if="isPending" class="mt-5 space-y-3" role="status">
      <span class="sr-only">{{ t('dashboard.health.loading') }}</span>
      <div v-for="index in 3" :key="index" class="h-5 animate-pulse rounded bg-surface-muted" />
    </div>

    <!-- Erro de comunicação com a API -->
    <div v-else-if="isError" class="mt-5 flex items-start gap-3" role="alert">
      <CircleAlert class="mt-0.5 size-5 shrink-0 text-danger" aria-hidden="true" />
      <div class="text-sm">
        <p class="font-medium text-text-primary">{{ errorMessage(error) }}</p>
        <p v-if="requestId" class="mt-1 text-text-secondary">
          {{ t('errors.requestId', { requestId }) }}
        </p>
      </div>
    </div>

    <!-- Resultado -->
    <div v-else-if="data" class="mt-5">
      <p class="flex items-center gap-2 text-sm font-medium text-text-primary" role="status">
        <component
          :is="healthy ? CircleCheck : CircleX"
          class="size-5"
          :class="healthy ? 'text-success' : 'text-danger'"
          aria-hidden="true"
        />
        {{ healthy ? t('dashboard.health.overall.ok') : t('dashboard.health.overall.unavailable') }}
      </p>

      <ul class="mt-4 divide-y divide-border rounded-md border border-border">
        <li
          v-for="[name, status] in checks"
          :key="name"
          class="flex items-center justify-between px-4 py-2.5 text-sm"
        >
          <span class="text-text-primary">{{ t(`dashboard.health.checks.${name}`) }}</span>
          <span class="flex items-center gap-1.5 font-medium text-text-primary">
            <component
              :is="status === 'ok' ? CircleCheck : CircleX"
              class="size-4"
              :class="status === 'ok' ? 'text-success' : 'text-danger'"
              aria-hidden="true"
            />
            {{ t(`dashboard.health.status.${status}`) }}
          </span>
        </li>
      </ul>

      <p class="mt-3 text-xs text-text-secondary tabular-nums">
        {{ t('dashboard.health.checkedAt', { time: formatTime(dataUpdatedAt) }) }}
      </p>
    </div>
  </section>
</template>
