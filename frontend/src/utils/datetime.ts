/** Formata um instante (UTC) no fuso horário do navegador do usuário. */
export function formatTime(value: Date | number, locale = 'pt-BR'): string {
  return new Intl.DateTimeFormat(locale, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(value)
}

/** Data e hora curtas no fuso do usuário (ex.: "04/10/2026 14:32"). */
export function formatDateTime(value: Date | number | string, locale = 'pt-BR'): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: 'short', timeStyle: 'short' }).format(
    typeof value === 'string' ? new Date(value) : value,
  )
}
