import type { AuditFilters, AuditLog } from '@/modules/audit/types'
import { http } from '@/services/http/client'
import type { Paginated } from '@/types/api'
import { localDayBoundsToUtc } from '@/utils/datetime'

export const AUDIT_PAGE_SIZE = 25

export async function listAuditLogs(filters: AuditFilters) {
  const params: Record<string, string | number> = {
    page: filters.page,
    page_size: AUDIT_PAGE_SIZE,
  }
  if (filters.search) params.search = filters.search
  if (filters.action) params.action = filters.action
  if (filters.entity_type) params.entity_type = filters.entity_type
  // Dias escolhidos no fuso de quem consulta; a API filtra em UTC.
  if (filters.from) params.occurred_after = localDayBoundsToUtc(filters.from).start
  if (filters.to) params.occurred_before = localDayBoundsToUtc(filters.to).end
  const { data } = await http.get<Paginated<AuditLog>>('/audit-logs', { params })
  return data
}
