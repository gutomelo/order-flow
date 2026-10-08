import type { RouteRecordRaw } from 'vue-router'

export const pricingRoutes: RouteRecordRaw[] = [
  {
    path: 'price-lists',
    name: 'price-lists',
    component: () => import('@/modules/pricing/pages/PriceListsPage.vue'),
    meta: { titleKey: 'pricing.title', permission: 'pricing:read' },
  },
  {
    path: 'price-lists/:id',
    name: 'price-list-detail',
    component: () => import('@/modules/pricing/pages/PriceListDetailPage.vue'),
    props: true,
    meta: { titleKey: 'pricing.title', permission: 'pricing:read' },
  },
]
