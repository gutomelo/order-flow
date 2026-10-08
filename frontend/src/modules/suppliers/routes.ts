import type { RouteRecordRaw } from 'vue-router'

export const suppliersRoutes: RouteRecordRaw[] = [
  {
    path: 'suppliers',
    name: 'suppliers',
    component: () => import('@/modules/suppliers/pages/SuppliersPage.vue'),
    meta: { titleKey: 'suppliers.title', permission: 'suppliers:read' },
  },
]
