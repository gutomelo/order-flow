import { useI18n } from 'vue-i18n'

import { ApiError } from '@/services/http/apiError'

/**
 * Mensagem exibível para um erro: códigos gerados no cliente (ex.: NETWORK_ERROR) vêm do i18n;
 * erros do backend já trazem `message` em pt-BR no envelope.
 */
export function useApiErrorMessage() {
  const { t, te } = useI18n()

  return (error: unknown): string => {
    if (error instanceof ApiError) {
      const key = `errors.${error.code}`
      return te(key) ? t(key) : error.message
    }
    return t('errors.UNKNOWN_ERROR')
  }
}
