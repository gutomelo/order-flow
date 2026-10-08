/**
 * Rótulos das barras a partir do início do intervalo **como o backend mandou** (fuso do negócio):
 * "2026-10-06T00:00:00-03:00" → "06/10" ou "00h". Converter para o fuso do navegador mudaria o dia.
 */
export function slotLabel(start: string, bucket: 'hour' | 'day'): string {
  const [date = '', time = ''] = start.split('T')
  const [, month = '', day = ''] = date.split('-')
  return bucket === 'hour' ? `${time.slice(0, 2)}h` : `${day}/${month}`
}

const integer = new Intl.NumberFormat('pt-BR')
export const formatCount = (value: number) => integer.format(value)

/**
 * Variação percentual para exibir (não é conta de dinheiro: o valor exibido vem do backend).
 * `null` quando não há base de comparação (período anterior zerado).
 */
export function percentChange(value: number, previous: number): number | null {
  if (previous === 0) return value === 0 ? 0 : null
  return Math.round(((value - previous) / Math.abs(previous)) * 100)
}
