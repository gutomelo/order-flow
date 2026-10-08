/**
 * CNPJ numérico e alfanumérico — espelho do validador do backend (shared/domain/documents.py)
 * apenas para feedback imediato no formulário. O backend é a autoridade.
 */
const FIRST_WEIGHTS = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
const SECOND_WEIGHTS = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

export function normalizeCnpj(value: string): string {
  return value.replace(/[.\-/\s]/g, '').toUpperCase()
}

function checkDigit(base: string, weights: number[]): number {
  const total = [...base].reduce(
    (sum, char, index) => sum + (char.charCodeAt(0) - 48) * (weights[index] ?? 0),
    0,
  )
  const remainder = total % 11
  return remainder < 2 ? 0 : 11 - remainder
}

export function isValidCnpj(value: string): boolean {
  const cnpj = normalizeCnpj(value)
  if (!/^[0-9A-Z]{12}[0-9]{2}$/.test(cnpj) || new Set(cnpj).size === 1) return false
  const first = checkDigit(cnpj.slice(0, 12), FIRST_WEIGHTS)
  const second = checkDigit(cnpj.slice(0, 12) + String(first), SECOND_WEIGHTS)
  return cnpj.slice(12) === `${first}${second}`
}
