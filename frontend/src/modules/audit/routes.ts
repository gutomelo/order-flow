import type { RouteRecordRaw } from 'vue-router'

export const auditRoutes: RouteRecordRaw[] = [
  {
    path: 'audit',
    name: 'audit',
    component: () => import('@/modules/audit/pages/AuditPage.vue'),
    meta: { titleKey: 'audit.title', permission: 'audit:read' },
  },
]
