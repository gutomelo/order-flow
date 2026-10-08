import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'

import { listAuditLogs } from '@/modules/audit/api/auditApi'
import type { AuditFilters } from '@/modules/audit/types'

export const auditKeys = {
  all: ['audit'] as const,
  list: (filters: AuditFilters) => [...auditKeys.all, 'list', filters] as const,
}

export function useAuditLogs(filters: MaybeRefOrGetter<AuditFilters>) {
  return useQuery({
    queryKey: computed(() => auditKeys.list(toValue(filters))),
    queryFn: () => listAuditLogs(toValue(filters)),
    placeholderData: keepPreviousData,
  })
}
