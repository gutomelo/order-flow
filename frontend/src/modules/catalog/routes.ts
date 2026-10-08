import type { RouteRecordRaw } from 'vue-router'

export const catalogRoutes: RouteRecordRaw[] = [
  {
    path: 'products',
    name: 'products',
    component: () => import('@/modules/catalog/pages/ProductsPage.vue'),
    meta: { titleKey: 'catalog.products.title', permission: 'catalog:read' },
  },
  {
    path: 'categories',
    name: 'categories',
    component: () => import('@/modules/catalog/pages/CategoriesPage.vue'),
    meta: { titleKey: 'catalog.categories.title', permission: 'catalog:read' },
  },
]
