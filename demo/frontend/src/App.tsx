// Top-level layout: header + two-column body (output | meter+timeline)
// + balances rail. Owns the session hook and the config fetch.

import { useCallback, useEffect, useState } from 'react'
import { AccessGate } from './components/AccessGate'
import { BalancePanel } from './components/BalancePanel'
import { ExplorerPanel } from './components/ExplorerPanel'
import { Header } from './components/Header'
import { MeterPanel } from './components/MeterPanel'
import { OutputPanel } from './components/OutputPanel'
import { PromptForm } from './components/PromptForm'
import { TimelinePanel } from './components/TimelinePanel'
import { WakingUpBanner } from './components/WakingUpBanner'
import { WakingUpOverlay } from './components/WakingUpOverlay'
import { useTapSession } from './hooks/useTapSession'
import { AccessDeniedError, fetchConfig } from './lib/api'
import type { ConfigResponse } from './lib/types'

// Show the cold-start overlay if the runner hasn't responded within this
// window. Render's free/Starter plans sleep after idle and the first
// request takes ~30s; tuned generously to avoid flashing the overlay on
// fast paths.
const COLD_START_DELAY_MS = 2500

// Show the in-session "waking the producer" banner if the session stays
// in `opening` past this delay. Same cold-start phenomenon, smaller UI —
// the user has just clicked send and we don't want to occlude the form.
const PRODUCER_WAKE_DELAY_MS = 3500

function App() {
  const [config, setConfig] = useState<ConfigResponse | null>(null)
  const [configError, setConfigError] = useState<string | null>(null)
  const [needsAccess, setNeedsAccess] = useState(false)
  const [wakingUp, setWakingUp] = useState(false)
  const { state, start, reset } = useTapSession()

  // Returns true once the runner is reachable AND the access code (if any)
  // is accepted. AccessGate uses the boolean to decide whether to surface
  // a "wrong code" message; the wake timer flips on the cold-start
  // overlay if Render's free tier is sleeping.
  const loadConfig = useCallback(async (): Promise<boolean> => {
    const wakeTimer = setTimeout(() => setWakingUp(true), COLD_START_DELAY_MS)
    try {
      const cfg = await fetchConfig()
      setConfig(cfg)
      setConfigError(null)
      setNeedsAccess(false)
      return true
    } catch (err) {
      if (err instanceof AccessDeniedError) {
        setNeedsAccess(true)
        setConfigError(null)
        return false
      }
      setConfigError((err as Error).message)
      return false
    } finally {
      clearTimeout(wakeTimer)
      setWakingUp(false)
    }
  }, [])

  useEffect(() => {
    void loadConfig()
  }, [loadConfig])

  // Producer cold-start detection: when a session hangs in `opening`
  // longer than expected, surface the inline banner. Resets the moment a
  // streaming/closed/error transition happens.
  const [producerWaking, setProducerWaking] = useState(false)
  useEffect(() => {
    if (state.phase !== 'opening') {
      setProducerWaking(false)
      return
    }
    const timer = setTimeout(() => setProducerWaking(true), PRODUCER_WAKE_DELAY_MS)
    return () => clearTimeout(timer)
  }, [state.phase])

  // Trigger balance refresh whenever a session closes — that's when
  // settled USDC actually moves on-chain (after the dispute window).
  const balanceRefreshKey = state.phase === 'closed' ? state.commits.length : 0

  return (
    <div className="min-h-screen flex flex-col">
      <WakingUpOverlay visible={wakingUp} />
      {needsAccess && <AccessGate onSubmit={loadConfig} />}
      <Header config={config} />
      <main className="mx-auto w-full max-w-[1400px] flex-1 px-6 py-6">
        {configError && (
          <div className="mb-6 rounded border border-[var(--color-danger)]/40 bg-[var(--color-danger-dim)] p-4 text-sm text-[var(--color-danger)]">
            <strong>Runner unreachable:</strong> {configError}
            <div className="mt-1 text-xs text-[var(--color-text-dim)]">
              Start it with{' '}
              <code className="font-mono">
                uvicorn demo.runner:app --port 8001
              </code>
              .
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-6">
          <div className="flex flex-col gap-6 min-w-0">
            <PromptForm onRun={start} onReset={reset} phase={state.phase} />
            <WakingUpBanner visible={producerWaking} />
            <div className="min-h-[480px]">
              <OutputPanel
                text={state.accumulated}
                phase={state.phase}
                haltedBy={state.haltedBy}
              />
            </div>
            <TimelinePanel channel={state.channel} commits={state.commits} />
            <ExplorerPanel
              channelId={state.channel?.channel_id ?? null}
              phase={state.phase}
            />
          </div>

          <aside className="flex flex-col gap-6">
            <MeterPanel
              tokens={state.tokens}
              paidMicro={state.paidMicro}
              prepaidInputMicro={state.channel?.prepaid_input_micro ?? 0}
              depositMicro={state.depositMicro}
              phase={state.phase}
              haltedBy={state.haltedBy}
              commitsCount={state.commits.length}
            />
            {config && <BalancePanel config={config} refreshKey={balanceRefreshKey} />}
          </aside>
        </div>

        {state.error && (
          <div className="mt-6 rounded border border-[var(--color-danger)]/40 bg-[var(--color-danger-dim)] p-4 font-mono text-xs text-[var(--color-danger)]">
            {state.error}
          </div>
        )}
      </main>

      <footer className="mt-auto border-t border-[var(--color-border)] px-6 py-4 text-center text-[11px] text-[var(--color-text-muted)]">
        TAP — Token Access Protocol · Solana Frontier 2026
      </footer>
    </div>
  )
}

export default App
