import { useI18n } from 'vue-i18n'

/** Códigos do provedor (`insufficient_funds`) em texto; código desconhecido aparece como veio. */
export function useProviderReason() {
  const { t, te } = useI18n()
  return (code: string) => (te(`payments.reasons.${code}`) ? t(`payments.reasons.${code}`) : code)
}
