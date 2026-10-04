import { z } from 'zod'

import { UNITS } from '@/modules/catalog/types'

// Espelho das regras do backend apenas para feedback imediato (docs/domain/catalog.md).
export const productSchema = z.object({
  sku: z
    .string()
    .trim()
    .regex(/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/, { error: 'validation.sku' }),
  name: z.string().trim().min(1, { error: 'validation.required' }).max(200),
  description: z.string(),
  unit: z.enum(UNITS),
  barcode: z
    .string()
    .trim()
    .regex(/^(|\d{8}|\d{12,14})$/, { error: 'validation.barcode' }),
  category_id: z.string(),
  default_supplier_id: z.string(),
})

export const categorySchema = z.object({
  name: z.string().trim().min(1, { error: 'validation.required' }).max(100),
  parent_id: z.string(),
})
