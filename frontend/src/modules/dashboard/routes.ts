import type { RouteRecordRaw } from 'vue-router'

export const dashboardRoutes: RouteRecordRaw[] = [
  {
    path: 'dashboard',
    name: 'dashboard',
    component: () => import('@/modules/dashboard/pages/DashboardPage.vue'),
    meta: { titleKey: 'dashboard.title' },
  },
]
