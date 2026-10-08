import { z } from 'zod'

// Mensagens são chaves i18n. A política de senha completa é do backend (validadores do Django).
export const forgotPasswordSchema = z.object({
  email: z.email({ error: 'validation.email' }),
})

export const resetPasswordSchema = z
  .object({
    password: z.string().min(8, { error: 'validation.passwordMin' }),
    confirmation: z.string(),
  })
  .superRefine((data, ctx) => {
    if (data.password !== data.confirmation) {
      ctx.addIssue({
        code: 'custom',
        path: ['confirmation'],
        message: 'validation.passwordMismatch',
      })
    }
  })
