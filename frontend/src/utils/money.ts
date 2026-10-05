/**
 * Dinheiro trafega como **string decimal** ("1234.50") e nunca vira `number` para contas:
 * totais são calculados pelo backend (POST /orders/quote). Aqui só formatação e leitura de input.
 */
const formatters = new Map<string, Intl.NumberFormat>()

export function formatMoney(amount: string | null | undefined, currency = 'BRL'): string {
  if (amount === null || amount === undefined || amount === '') return '—'
  let formatter = formatters.get(currency)
  if (!formatter) {
    formatter = new Intl.NumberFormat('pt-BR', { style: 'currency', currency })
    formatters.set(currency, formatter)
  }
  // `Number` só para exibir (precisão de 2 casas é preservada para valores de até 15 dígitos).
  return formatter.format(Number(amount))
}

/** "3,50" | "1.234,5" | "1234.50" → "1234.50"; vazio ou inválido → null. */
export function parseMoneyInput(raw: string): string | null {
  const value = raw.trim().replace(/\s|R\$/g, '')
  if (!value) return null
  const normalized = value.includes(',') ? value.replace(/\./g, '').replace(',', '.') : value
  if (!/^\d+(\.\d{1,2})?$/.test(normalized)) return null
  const [integer = '0', cents = ''] = normalized.split('.')
  return `${String(Number(integer))}.${cents.padEnd(2, '0')}`
}

/** "1234.50" → "1234,50" para preencher inputs. */
export function toMoneyInput(amount: string): string {
  return amount.replace('.', ',')
}
