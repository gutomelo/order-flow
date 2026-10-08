import type { RouteRecordRaw } from 'vue-router'

export const inventoryRoutes: RouteRecordRaw[] = [
  {
    path: 'stock',
    name: 'stock',
    component: () => import('@/modules/inventory/pages/StockPage.vue'),
    meta: { titleKey: 'inventory.stock.title', permission: 'inventory:read' },
  },
  {
    path: 'movements',
    name: 'movements',
    component: () => import('@/modules/inventory/pages/MovementsPage.vue'),
    meta: { titleKey: 'inventory.movements.title', permission: 'inventory:read' },
  },
  {
    path: 'warehouses',
    name: 'warehouses',
    component: () => import('@/modules/inventory/pages/WarehousesPage.vue'),
    meta: { titleKey: 'inventory.warehouses.title', permission: 'inventory:read' },
  },
]
