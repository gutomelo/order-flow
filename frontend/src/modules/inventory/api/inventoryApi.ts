import type {
  StockAvailability,
  MovementFilters,
  ReceiptInput,
  StockFilters,
  StockItem,
  StockMovement,
  Warehouse,
} from '@/modules/inventory/types'
import { http } from '@/services/http/client'
import type { Paginated } from '@/types/api'
import { localDayBoundsToUtc } from '@/utils/datetime'

export const STOCK_PAGE_SIZE = 25
export const MOVEMENTS_PAGE_SIZE = 50

export async function getAvailability(warehouseId: string, productIds: string[]) {
  const { data } = await http.get<StockAvailability[]>('/inventory/availability', {
    params: { warehouse: warehouseId, products: productIds.join(',') },
  })
  return data
}

export async function listWarehouses() {
  const { data } = await http.get<Warehouse[]>('/inventory/warehouses')
  return data
}

export async function createWarehouse(input: { code: string; name: string }) {
  const { data } = await http.post<Warehouse>('/inventory/warehouses', input)
  return data
}

export async function renameWarehouse(id: string, name: string) {
  const { data } = await http.patch<Warehouse>(`/inventory/warehouses/${id}`, { name })
  return data
}

export async function setWarehouseActive(id: string, active: boolean) {
  const { data } = await http.post<Warehouse>(
    `/inventory/warehouses/${id}/${active ? 'activate' : 'deactivate'}`,
  )
  return data
}

export async function listStock(filters: StockFilters) {
  const params: Record<string, string | number> = { page: filters.page, page_size: STOCK_PAGE_SIZE }
  if (filters.search) params.search = filters.search
  if (filters.warehouse) params.warehouse = filters.warehouse
  if (filters.low) params.low_stock = 'true'
  const { data } = await http.get<Paginated<StockItem>>('/inventory/stock-items', { params })
  return data
}

export async function getStockItem(id: string) {
  const { data } = await http.get<StockItem>(`/inventory/stock-items/${id}`)
  return data
}

export async function setReorderPoint(id: string, reorderPoint: number) {
  const { data } = await http.patch<StockItem>(`/inventory/stock-items/${id}`, {
    reorder_point: reorderPoint,
  })
  return data
}

export async function listMovements(filters: MovementFilters) {
  const params: Record<string, string | number> = {
    page: filters.page,
    page_size: MOVEMENTS_PAGE_SIZE,
  }
  if (filters.search) params.search = filters.search
  if (filters.type) params.type = filters.type
  if (filters.warehouse) params.warehouse = filters.warehouse
  if (filters.product) params.product = filters.product
  // O período é escolhido em dias do fuso do usuário e enviado como instantes UTC.
  if (filters.from) params.created_after = localDayBoundsToUtc(filters.from).start
  if (filters.to) params.created_before = localDayBoundsToUtc(filters.to).end
  const { data } = await http.get<Paginated<StockMovement>>('/inventory/movements', { params })
  return data
}

export async function receiveStock(input: ReceiptInput) {
  const { data } = await http.post('/inventory/receipts', input)
  return data
}

export async function adjustStock(input: {
  stock_item_id: string
  counted_quantity: number
  expected_on_hand: number
  reason: string
}) {
  const { data } = await http.post<StockItem>('/inventory/adjustments', input)
  return data
}

export async function transferStock(input: {
  stock_item_id: string
  to_warehouse_id: string
  quantity: number
  reason: string
}) {
  const { data } = await http.post('/inventory/transfers', input)
  return data
}
