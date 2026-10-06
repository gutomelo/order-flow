import type { RouteRecordRaw } from 'vue-router'

export const paymentsRoutes: RouteRecordRaw[] = [
  {
    path: 'payments',
    name: 'payments',
    component: () => import('@/modules/payments/pages/PaymentsPage.vue'),
    meta: { titleKey: 'payments.title', permission: 'payments:read' },
  },
]
