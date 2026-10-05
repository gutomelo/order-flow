import { z } from 'zod'

import { parseMoneyInput } from '@/utils/money'

/** Preço digitado em pt-BR ("3,50") → string decimal da API ("3.50"). */
export const moneyInput = z
  .string()
  .refine((value) => parseMoneyInput(value) !== null, { error: 'validation.money' })
  .transform((value) => parseMoneyInput(value) ?? '')

export const priceListSchema = z.object({
  name: z.string().trim().min(1, { error: 'validation.required' }).max(120),
  // 'default' = tabela padrão; senão, o id do segmento.
  target: z.string().min(1, { error: 'validation.required' }),
})

export const priceItemSchema = z.object({ unit_price: moneyInput })
