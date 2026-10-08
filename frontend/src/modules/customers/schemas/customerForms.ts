import { z } from 'zod'

import { BRAZILIAN_STATES, normalizePostalCode } from '@/modules/customers/addresses'
import { isValidCnpj } from '@/utils/documents'

const required = (max: number) =>
  z.string().trim().min(1, { error: 'validation.required' }).max(max)
const email = z.union([z.literal(''), z.email({ error: 'validation.email' })])

export const customerSchema = z.object({
  legal_name: required(200),
  trade_name: z.string().trim().max(200),
  tax_id: z.string().refine(isValidCnpj, { error: 'validation.cnpj' }),
  email,
  phone: z.string().trim().max(30),
  // '' no <select> = sem segmento.
  segment_id: z.string().transform((value) => value || null),
})

export const segmentSchema = z.object({
  code: z
    .string()
    .trim()
    .regex(/^[A-Za-z0-9_-]{2,30}$/, { error: 'validation.segmentCode' }),
  name: required(120),
  description: z.string().trim().max(500),
})

export const addressSchema = z.object({
  label: required(60),
  postal_code: z
    .string()
    .refine((value) => normalizePostalCode(value).length === 8, { error: 'validation.postalCode' }),
  street: required(200),
  number: required(20),
  complement: z.string().trim().max(100),
  district: required(100),
  city: required(100),
  state: z.string().refine((value) => (BRAZILIAN_STATES as readonly string[]).includes(value), {
    error: 'validation.required',
  }),
})

export const contactSchema = z
  .object({
    name: required(120),
    job_title: z.string().trim().max(80),
    email,
    phone: z.string().trim().max(30),
  })
  // CT1: espelha a regra do backend só para feedback imediato.
  .refine((value) => value.email !== '' || value.phone !== '', {
    error: 'validation.contactChannel',
    path: ['email'],
  })
