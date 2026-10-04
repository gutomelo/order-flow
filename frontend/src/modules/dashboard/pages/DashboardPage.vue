<script setup lang="ts">
import { ChartNoAxesColumn } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import EmptyState from '@/components/ui/EmptyState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SystemHealthCard from '@/modules/dashboard/components/SystemHealthCard.vue'

const { t } = useI18n()
</script>

<template>
  <div>
    <PageHeader :title="t('dashboard.title')" :description="t('dashboard.description')" />

    <div class="grid gap-6 xl:grid-cols-3">
      <EmptyState
        class="xl:col-span-2"
        :title="t('dashboard.empty.title')"
        :description="t('dashboard.empty.description')"
        :icon="ChartNoAxesColumn"
      />
      <SystemHealthCard />
    </div>
  </div>
</template>
