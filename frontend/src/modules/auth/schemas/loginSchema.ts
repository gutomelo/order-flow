import { z } from 'zod'

// Mensagens são chaves i18n, traduzidas na renderização (useZodForm).
export const loginSchema = z.object({
  email: z.email({ error: 'validation.email' }),
  password: z.string().min(1, { error: 'validation.required' }),
})

export type LoginForm = z.infer<typeof loginSchema>
