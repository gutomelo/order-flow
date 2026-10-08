import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'

import { getDashboard } from '@/modules/dashboard/api/dashboardApi'
import type { DashboardPeriod } from '@/modules/dashboard/types'

// Mesmo intervalo do cache do backend: atualizar mais rápido só devolveria o mesmo número.
const REFRESH_MS = 60_000

export function useDashboard(period: MaybeRefOrGetter<DashboardPeriod>) {
  return useQuery({
    queryKey: computed(() => ['dashboard', toValue(period)] as const),
    queryFn: () => getDashboard(toValue(period)),
    // Trocar o período mantém os números anteriores na tela (esmaecidos) até chegar o novo.
    placeholderData: keepPreviousData,
    refetchInterval: REFRESH_MS,
  })
}
