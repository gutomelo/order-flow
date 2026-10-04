import { createI18n } from 'vue-i18n'

import ptBR from '@/app/i18n/locales/pt-BR'

export type MessageSchema = typeof ptBR

export function createAppI18n() {
  return createI18n<[MessageSchema], 'pt-BR'>({
    legacy: false,
    locale: 'pt-BR',
    fallbackLocale: 'pt-BR',
    messages: { 'pt-BR': ptBR },
  })
}

export const i18n = createAppI18n()
