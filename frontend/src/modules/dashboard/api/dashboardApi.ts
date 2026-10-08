import type { DashboardData, DashboardPeriod } from '@/modules/dashboard/types'
import { http } from '@/services/http/client'

export async function getDashboard(period: DashboardPeriod) {
  const { data } = await http.get<DashboardData>('/dashboard', { params: { period } })
  return data
}
