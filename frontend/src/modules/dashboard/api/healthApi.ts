import { createHttpClient } from '@/services/http/client'

export type HealthStatus = 'ok' | 'unavailable'

export interface ReadinessReport {
  status: HealthStatus
  checks: Record<string, HealthStatus>
}

// Health checks ficam fora de /api/v1 (são infraestrutura, não recurso de negócio).
const healthHttp = createHttpClient('')

export async function fetchReadiness(): Promise<ReadinessReport> {
  const { data } = await healthHttp.get<ReadinessReport>('/health/ready', {
    // 503 também traz o relatório de quais dependências falharam.
    validateStatus: (status) => status === 200 || status === 503,
  })
  return data
}
