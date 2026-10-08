import { z } from 'zod'

import { ROLES } from '@/modules/auth/types'

// Mensagens são chaves i18n. A política completa de senha é do backend (validadores do Django);
// aqui só o mínimo para feedback imediato.
const profile = {
  first_name: z.string().trim().min(1, { error: 'validation.required' }).max(150),
  last_name: z.string().trim().max(150),
  role: z.enum(ROLES, { error: 'validation.required' }),
  team_id: z.string(),
}

/** Convite: a pessoa recebe um link e define a própria senha (ninguém mais a conhece). */
export const ACCESS_MODES = ['invite', 'password'] as const

export const createUserSchema = z
  .object({
    ...profile,
    email: z.email({ error: 'validation.email' }),
    access: z.enum(ACCESS_MODES),
    password: z.string(),
  })
  .superRefine((data, ctx) => {
    if (data.access === 'password' && data.password.length < 8) {
      ctx.addIssue({ code: 'custom', path: ['password'], message: 'validation.passwordMin' })
    }
  })

// Edição: mesmos campos do formulário, mas e-mail, acesso e senha não são editados.
export const editUserSchema = z.object({
  ...profile,
  email: z.string(),
  access: z.string(),
  password: z.string(),
})

export const teamSchema = z.object({
  name: z.string().trim().min(1, { error: 'validation.required' }).max(100),
})
