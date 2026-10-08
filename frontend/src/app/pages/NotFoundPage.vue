<script setup lang="ts">
import { SearchX } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import EmptyState from '@/components/ui/EmptyState.vue'

const { t } = useI18n()
</script>

<template>
  <EmptyState :title="t('notFound.title')" :description="t('notFound.description')" :icon="SearchX">
    <template #action>
      <RouterLink
        :to="{ name: 'dashboard' }"
        class="inline-flex h-9 items-center rounded-md bg-primary px-4 text-sm font-medium text-on-primary hover:bg-primary-hover"
      >
        {{ t('notFound.backToDashboard') }}
      </RouterLink>
    </template>
  </EmptyState>
</template>
