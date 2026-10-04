/** Formata um instante (UTC) no fuso horário do navegador do usuário. */
export function formatTime(value: Date | number, locale = 'pt-BR'): string {
  return new Intl.DateTimeFormat(locale, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(value)
}
