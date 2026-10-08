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

/**
 * Converte um dia do calendário local (YYYY-MM-DD) no intervalo UTC [início, início do dia
 * seguinte). O banco guarda UTC; o usuário escolhe dias no próprio fuso.
 */
export function localDayBoundsToUtc(day: string): { start: string; end: string } {
  const [year, month, date] = day.split('-').map(Number)
  const start = new Date(year ?? 1970, (month ?? 1) - 1, date ?? 1)
  const end = new Date(start)
  end.setDate(end.getDate() + 1)
  return { start: start.toISOString(), end: end.toISOString() }
}
