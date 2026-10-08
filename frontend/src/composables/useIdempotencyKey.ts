/**
 * Idempotency-Key por **intenção** (ADR-012): a mesma chave enquanto o conteúdo enviado não muda.
 *
 * Se a primeira tentativa expirou no cliente mas foi processada no servidor, reenviar o mesmo
 * conteúdo reaproveita a chave e recebe a resposta original — sem pedido duplicado. Mudar o
 * conteúdo é outra intenção: nova chave.
 */
export function useIdempotencyKey(source: () => unknown): () => string {
  let fingerprint: string | null = null
  let key = crypto.randomUUID()
  return () => {
    const next = JSON.stringify(source())
    if (next !== fingerprint) {
      fingerprint = next
      key = crypto.randomUUID()
    }
    return key
  }
}
