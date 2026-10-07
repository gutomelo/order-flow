export type DashboardPeriod = 'today' | '7d' | '30d'

/** Valor do período e do período anterior de mesmo tamanho (para a variação). */
export interface Comparison<T> {
  value: T
  previous: T
}

export interface DashboardData {
  period: DashboardPeriod
  start: string
  end: string
  bucket: 'hour' | 'day'
  /** Quando os números foram calculados (cache de até 1 minuto no backend). */
  generated_at: string
  orders: {
    submitted: Comparison<number>
    series: { start: string; count: number }[]
    open_by_status: { status: string; count: number }[]
    recent: {
      id: string
      reference: string
      customer_name: string
      status: string
      total: string
      submitted_at: string
    }[]
  }
  /** `null` sem `reports:financial`. Dinheiro em string decimal. */
  money: {
    revenue: Comparison<string>
    refunded: Comparison<string>
    paid_orders: Comparison<number>
    average_ticket: Comparison<string | null>
    series: { start: string; net: string }[]
  } | null
  /** `null` sem `inventory:read`. */
  stock: { low_stock_items: number } | null
}
