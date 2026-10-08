import { useQuery } from '@tanstack/vue-query'

import { fetchReadiness } from '@/modules/dashboard/api/healthApi'

export const dashboardKeys = {
  all: ['dashboard'] as const,
  readiness: () => [...dashboardKeys.all, 'readiness'] as const,
}

const REFRESH_INTERVAL_MS = 30_000

export function useSystemHealth() {
  return useQuery({
    queryKey: dashboardKeys.readiness(),
    queryFn: fetchReadiness,
    refetchInterval: REFRESH_INTERVAL_MS,
  })
}
