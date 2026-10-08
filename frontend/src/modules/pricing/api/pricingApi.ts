import type { PriceItemFilters, PriceList, PriceListItem } from '@/modules/pricing/types'
import { http } from '@/services/http/client'
import type { Paginated } from '@/types/api'

export const PRICE_ITEMS_PAGE_SIZE = 25

export async function listPriceLists() {
  const { data } = await http.get<PriceList[]>('/price-lists')
  return data
}

export async function getPriceList(id: string) {
  const { data } = await http.get<PriceList>(`/price-lists/${id}`)
  return data
}

export async function createPriceList(input: { name: string; segment_id: string | null }) {
  const { data } = await http.post<PriceList>('/price-lists', input)
  return data
}

export async function renamePriceList(id: string, name: string) {
  const { data } = await http.patch<PriceList>(`/price-lists/${id}`, { name })
  return data
}

export async function deletePriceList(id: string) {
  await http.delete(`/price-lists/${id}`)
}

export async function listPriceItems(priceListId: string, filters: PriceItemFilters) {
  const params: Record<string, string | number> = {
    page: filters.page,
    page_size: PRICE_ITEMS_PAGE_SIZE,
  }
  if (filters.search) params.search = filters.search
  const { data } = await http.get<Paginated<PriceListItem>>(`/price-lists/${priceListId}/items`, {
    params,
  })
  return data
}

export async function savePriceItem(
  priceListId: string,
  input: { product_id?: string; unit_price: string },
  id?: string,
) {
  const base = `/price-lists/${priceListId}/items`
  const { data } = id
    ? await http.patch<PriceListItem>(`${base}/${id}`, { unit_price: input.unit_price })
    : await http.post<PriceListItem>(base, input)
  return data
}

export async function removePriceItem(priceListId: string, id: string) {
  await http.delete(`/price-lists/${priceListId}/items/${id}`)
}
