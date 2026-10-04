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

export const createUserSchema = z.object({
  ...profile,
  email: z.email({ error: 'validation.email' }),
  password: z.string().min(8, { error: 'validation.passwordMin' }),
})

// Edição: mesmos campos do formulário, mas e-mail e senha não são editados nem validados.
export const editUserSchema = createUserSchema.extend({ email: z.string(), password: z.string() })

export const teamSchema = z.object({
  name: z.string().trim().min(1, { error: 'validation.required' }).max(100),
})
