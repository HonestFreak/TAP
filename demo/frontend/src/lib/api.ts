// Thin REST + SSE client targeting the consumer runner backend.
//
// The browser EventSource API only supports GET — we POST a session start
// and then read the streaming SSE response with `fetch` + a manual reader.
// Each `data: {...}\n\n` block is parsed and pushed as a typed event.

import type { BalancesResponse, ConfigResponse, SessionEvent } from './types'

export async function fetchConfig(): Promise<ConfigResponse> {
  const r = await fetch('/api/config')
  if (!r.ok) throw new Error(`config fetch failed: ${r.status}`)
  return r.json()
}

export async function fetchBalances(): Promise<BalancesResponse> {
  const r = await fetch('/api/balances')
  if (!r.ok) throw new Error(`balances fetch failed: ${r.status}`)
  return r.json()
}

export interface RunOptions {
  prompt: string
  depositMicro: number
  enforceSchema: boolean
  signal?: AbortSignal
  onEvent: (event: SessionEvent) => void
}

export async function runSession(opts: RunOptions): Promise<void> {
  const response = await fetch('/api/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify({
      prompt: opts.prompt,
      deposit_micro: opts.depositMicro,
      enforce_schema: opts.enforceSchema,
    }),
    signal: opts.signal,
  })

  if (!response.ok || !response.body) {
    throw new Error(`run request failed: ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) return
    buffer += decoder.decode(value, { stream: true })

    // SSE messages are separated by blank lines.
    let boundary = buffer.indexOf('\n\n')
    while (boundary !== -1) {
      const raw = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)
      const dataLine = raw
        .split('\n')
        .find((line) => line.startsWith('data:'))
      if (dataLine) {
        const json = dataLine.slice(5).trim()
        try {
          opts.onEvent(JSON.parse(json) as SessionEvent)
        } catch (err) {
          console.warn('failed to parse SSE event', err, json)
        }
      }
      boundary = buffer.indexOf('\n\n')
    }
  }
}
