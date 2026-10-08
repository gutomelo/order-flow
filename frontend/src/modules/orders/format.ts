/** Nº do pedido para exibição: 1 → "#000001". Rascunhos não têm número. */
export function formatOrderNumber(number: number | null): string | null {
  return number === null ? null : `#${String(number).padStart(6, '0')}`
}
