// Single-purpose hook: runs one TAP session and exposes its derived state.
//
// State is shaped so each panel can pluck what it needs without re-deriving:
//   * phase           — current lifecycle stage
//   * tokens          — running counter of tokens received
//   * paidMicro       — cumulative paid in micro-USDC
//   * accumulated     — full streamed text so far
//   * commits         — array of signed commitment events (newest last)
//   * channel         — channel-open metadata (set once)
//   * haltedBy        — non-null when an evaluator triggered a halt
//   * error           — non-null on protocol/network failure

import { useCallback, useRef, useState } from 'react'
import { runSession } from '../lib/api'
import type {
  CommitSignedEvent,
  SessionOpenEvent,
  SessionPhase,
} from '../lib/types'

export interface SessionState {
  phase: SessionPhase
  tokens: number
  paidMicro: number
  accumulated: string
  commits: CommitSignedEvent[]
  channel: SessionOpenEvent | null
  haltedBy: string | null
  error: string | null
  depositMicro: number
}

const initial: SessionState = {
  phase: 'idle',
  tokens: 0,
  paidMicro: 0,
  accumulated: '',
  commits: [],
  channel: null,
  haltedBy: null,
  error: null,
  depositMicro: 0,
}

export function useTapSession() {
  const [state, setState] = useState<SessionState>(initial)
  const abortRef = useRef<AbortController | null>(null)

  const start = useCallback(
    async (prompt: string, depositMicro: number, enforceSchema: boolean) => {
      abortRef.current?.abort()
      const ctrl = new AbortController()
      abortRef.current = ctrl

      setState({ ...initial, phase: 'opening', depositMicro })

      try {
        await runSession({
          prompt,
          depositMicro,
          enforceSchema,
          signal: ctrl.signal,
          onEvent: (event) => {
            setState((prev) => {
              switch (event.type) {
                case 'phase':
                  return { ...prev, phase: event.phase }
                case 'session_open':
                  // Seed `paidMicro` with the prepaid input cost so the meter
                  // reflects the on-chain floor immediately at session open
                  // (whitepaper §4.9), before any output token arrives.
                  return {
                    ...prev,
                    channel: event,
                    paidMicro: event.prepaid_input_micro,
                  }
                case 'token':
                  return {
                    ...prev,
                    tokens: event.tokens_received,
                    paidMicro: event.cumulative_paid_micro,
                    accumulated: prev.accumulated + event.text,
                  }
                case 'commit_signed':
                  return { ...prev, commits: [...prev.commits, event] }
                case 'complete':
                  return {
                    ...prev,
                    phase: 'closed',
                    tokens: event.tokens_received,
                    paidMicro: event.cumulative_paid_micro,
                    haltedBy: event.halted_by,
                  }
                case 'error':
                  return { ...prev, phase: 'error', error: event.message }
              }
            })
          },
        })
      } catch (err) {
        if ((err as Error).name === 'AbortError') return
        setState((prev) => ({ ...prev, phase: 'error', error: (err as Error).message }))
      }
    },
    [],
  )

  const reset = useCallback(() => {
    abortRef.current?.abort()
    setState(initial)
  }, [])

  return { state, start, reset }
}
