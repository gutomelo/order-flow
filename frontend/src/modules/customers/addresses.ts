/** UFs aceitas pelo backend (`BrazilianState`); os nomes vêm do i18n (`customers.states`). */
export const BRAZILIAN_STATES = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA',
  'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
] as const // prettier-ignore

export type BrazilianState = (typeof BRAZILIAN_STATES)[number]

export function normalizePostalCode(value: string): string {
  return value.replace(/\D/g, '')
}

/** "01310100" → "01310-100"; valores incompletos ficam como estão. */
export function formatPostalCode(value: string): string {
  const digits = normalizePostalCode(value)
  return digits.length === 8 ? `${digits.slice(0, 5)}-${digits.slice(5)}` : value
}
