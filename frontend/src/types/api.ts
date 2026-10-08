/** Resposta paginada padrão da API (shared.pagination.DefaultPagination). */
export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
