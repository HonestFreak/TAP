// Thin REST + SSE client targeting the consumer runner backend.
//
// The browser EventSource API only supports GET — we POST a session start
// and then read the streaming SSE response with `fetch` + a manual reader.
// Each `data: {...}\n\n` block is parsed and pushed as a typed event.

import type {
  BalancesResponse,
  ChannelSignaturesResponse,
  ConfigResponse,
  SessionEvent,
} from './types'

// In dev the Vite proxy maps `/api` → localhost:8001, so an empty base is
// what we want. In production the runner is on a different origin and
// VITE_API_BASE is set at build time (e.g. https://tap-runner.example.com).
const API_BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '')

const ACCESS_STORAGE_KEY = 'tap-access-code'

export class AccessDeniedError extends Error {
  constructor() {
    super('access denied')
    this.name = 'AccessDeniedError'
  }
}

export function getAccessCode(): string {
  return localStorage.getItem(ACCESS_STORAGE_KEY) ?? ''
}

export function setAccessCode(code: string): void {
  localStorage.setItem(ACCESS_STORAGE_KEY, code)
}

export function clearAccessCode(): void {
  localStorage.removeItem(ACCESS_STORAGE_KEY)
}

function authHeaders(extra: HeadersInit = {}): HeadersInit {
  const code = getAccessCode()
  const headers: Record<string, string> = { ...(extra as Record<string, string>) }
  if (code) headers['X-Tap-Access'] = code
  return headers
}

async function checkAuth(response: Response): Promise<void> {
  if (response.status === 401) throw new AccessDeniedError()
}

export async function fetchConfig(): Promise<ConfigResponse> {
  const r = await fetch(`${API_BASE}/api/config`, { headers: authHeaders() })
  await checkAuth(r)
  if (!r.ok) throw new Error(`config fetch failed: ${r.status}`)
  return r.json()
}

export async function fetchBalances(): Promise<BalancesResponse> {
  const r = await fetch(`${API_BASE}/api/balances`, { headers: authHeaders() })
  await checkAuth(r)
  if (!r.ok) throw new Error(`balances fetch failed: ${r.status}`)
  return r.json()
}

export async function fetchChannelSignatures(
  channelId: string,
): Promise<ChannelSignaturesResponse> {
  const r = await fetch(
    `${API_BASE}/api/sessions/${encodeURIComponent(channelId)}/signatures`,
    { headers: authHeaders() },
  )
  await checkAuth(r)
  if (!r.ok) throw new Error(`signatures fetch failed: ${r.status}`)
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
  const response = await fetch(`${API_BASE}/api/run`, {
    method: 'POST',
    headers: authHeaders({
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    }),
    body: JSON.stringify({
      prompt: opts.prompt,
      deposit_micro: opts.depositMicro,
      enforce_schema: opts.enforceSchema,
    }),
    signal: opts.signal,
  })
  await checkAuth(response)

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
