import type { RouteRecordRaw } from 'vue-router'

export const customersRoutes: RouteRecordRaw[] = [
  {
    path: 'customers',
    name: 'customers',
    component: () => import('@/modules/customers/pages/CustomersPage.vue'),
    meta: { titleKey: 'customers.title', permission: 'customers:read' },
  },
  {
    path: 'customers/:id',
    name: 'customer-detail',
    component: () => import('@/modules/customers/pages/CustomerDetailPage.vue'),
    props: true,
    meta: { titleKey: 'customers.detail.title', permission: 'customers:read' },
  },
  {
    path: 'customer-segments',
    name: 'customer-segments',
    component: () => import('@/modules/customers/pages/SegmentsPage.vue'),
    meta: { titleKey: 'segments.title', permission: 'customers:read' },
  },
]
