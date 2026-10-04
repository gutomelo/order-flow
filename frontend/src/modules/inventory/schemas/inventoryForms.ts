import { z } from 'zod'

/** Quantidade inteira digitada como texto (inputmode numérico). */
export const quantity = (min: number) =>
  z
    .string()
    .trim()
    .regex(/^\d+$/, { error: 'validation.integer' })
    .transform(Number)
    .refine((value) => value >= min, {
      error: min > 0 ? 'validation.positive' : 'validation.integer',
    })

export const receiptHeaderSchema = z.object({
  warehouse_id: z.string().min(1, { error: 'validation.required' }),
  supplier_id: z.string(),
  document_number: z.string().trim().max(60),
  notes: z.string(),
})

export const adjustmentSchema = z.object({
  counted_quantity: quantity(0),
  reason: z.string().trim().min(5, { error: 'validation.reasonMin' }).max(500),
})

export const transferSchema = z.object({
  to_warehouse_id: z.string().min(1, { error: 'validation.required' }),
  quantity: quantity(1),
  reason: z.string().trim().max(500),
})

export const reorderPointSchema = z.object({ reorder_point: quantity(0) })

export const warehouseSchema = z.object({
  code: z
    .string()
    .trim()
    .regex(/^[A-Za-z0-9-]{2,20}$/, { error: 'validation.warehouseCode' }),
  name: z.string().trim().min(1, { error: 'validation.required' }).max(120),
})
