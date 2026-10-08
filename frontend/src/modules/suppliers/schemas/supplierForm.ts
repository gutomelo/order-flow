import { z } from 'zod'

import { isValidCnpj } from '@/utils/documents'

export const supplierSchema = z.object({
  legal_name: z.string().trim().min(1, { error: 'validation.required' }).max(200),
  trade_name: z.string().trim().max(200),
  tax_id: z.string().refine(isValidCnpj, { error: 'validation.cnpj' }),
  email: z.union([z.literal(''), z.email({ error: 'validation.email' })]),
  phone: z.string().trim().max(30),
})
