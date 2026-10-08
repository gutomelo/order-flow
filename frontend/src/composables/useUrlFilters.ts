import { computed } from 'vue'
import { useRoute, useRouter, type LocationQueryValue } from 'vue-router'

type FilterValue = string | number

/**
 * Filtros de listagem guardados na query string: compartilháveis por link e preservados ao usar
 * o "voltar" do navegador. Valores iguais ao default não aparecem na URL.
 *
 * `page` volta para 1 sempre que outro filtro muda.
 */
export function useUrlFilters<T extends { [K in keyof T]: FilterValue } & { page: number }>(
  defaults: T,
  parse: { [K in keyof T]?: (raw: string) => T[K] | undefined } = {},
) {
  const route = useRoute()
  const router = useRouter()

  function readOne<K extends keyof T>(key: K): T[K] {
    const raw: LocationQueryValue | LocationQueryValue[] | undefined = route.query[key as string]
    const value = Array.isArray(raw) ? raw[0] : raw
    if (typeof value !== 'string' || value === '') return defaults[key]
    const parser = parse[key]
    if (parser) return parser(value) ?? defaults[key]
    if (typeof defaults[key] === 'number') {
      const number = Number(value)
      return (Number.isFinite(number) && number > 0 ? number : defaults[key]) as T[K]
    }
    return value as T[K]
  }

  const filters = computed<T>(() => {
    const result = { ...defaults }
    for (const key of Object.keys(defaults) as (keyof T)[]) {
      result[key] = readOne(key)
    }
    return result
  })

  function update(patch: Partial<T>) {
    const next: T = { ...filters.value, page: 1, ...patch }
    const query: Record<string, string> = {}
    for (const key of Object.keys(next) as (keyof T & string)[]) {
      if (next[key] !== defaults[key]) query[key] = String(next[key])
    }
    void router.replace({ query })
  }

  /** v-model para um filtro (ex.: `<select v-model="field('role').value">`). */
  function field<K extends keyof T>(key: K) {
    return computed({
      get: () => filters.value[key],
      set: (value: T[K]) => update({ [key]: value } as unknown as Partial<T>),
    })
  }

  const hasActiveFilters = computed(() =>
    (Object.keys(defaults) as (keyof T)[]).some(
      (key) => key !== 'page' && filters.value[key] !== defaults[key],
    ),
  )

  return { filters, update, field, hasActiveFilters }
}
