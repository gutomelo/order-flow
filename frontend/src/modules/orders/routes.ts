import type { RouteRecordRaw } from 'vue-router'

export const ordersRoutes: RouteRecordRaw[] = [
  {
    path: 'orders',
    name: 'orders',
    component: () => import('@/modules/orders/pages/OrdersPage.vue'),
    meta: { titleKey: 'orders.title', permission: 'orders:read' },
  },
  {
    path: 'orders/new',
    name: 'order-new',
    component: () => import('@/modules/orders/pages/OrderEditorPage.vue'),
    meta: { titleKey: 'orders.editor.newTitle', permission: 'orders:create' },
  },
  {
    path: 'orders/:id/edit',
    name: 'order-edit',
    component: () => import('@/modules/orders/pages/OrderEditorPage.vue'),
    props: true,
    meta: { titleKey: 'orders.editor.editTitle', permission: 'orders:create' },
  },
  {
    path: 'fulfillment',
    name: 'fulfillment',
    component: () => import('@/modules/orders/pages/FulfillmentPage.vue'),
    meta: { titleKey: 'orders.fulfillment.queue.title', permission: 'orders:process' },
  },
  {
    path: 'orders/:id',
    name: 'order-detail',
    component: () => import('@/modules/orders/pages/OrderDetailPage.vue'),
    props: true,
    meta: { titleKey: 'orders.detail.title', permission: 'orders:read' },
  },
]
