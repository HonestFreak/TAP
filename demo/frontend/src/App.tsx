// Top-level layout: header + two-column body (output | meter+timeline)
// + balances rail. Owns the session hook and the config fetch.

import { useEffect, useState } from 'react'
import { BalancePanel } from './components/BalancePanel'
import { Header } from './components/Header'
import { MeterPanel } from './components/MeterPanel'
import { OutputPanel } from './components/OutputPanel'
import { PromptForm } from './components/PromptForm'
import { TimelinePanel } from './components/TimelinePanel'
import { useTapSession } from './hooks/useTapSession'
import { fetchConfig } from './lib/api'
import type { ConfigResponse } from './lib/types'

function App() {
  const [config, setConfig] = useState<ConfigResponse | null>(null)
  const [configError, setConfigError] = useState<string | null>(null)
  const { state, start, reset } = useTapSession()

  useEffect(() => {
    fetchConfig()
      .then(setConfig)
      .catch((err) => setConfigError(err.message))
  }, [])

  // Trigger balance refresh whenever a session closes — that's when
  // settled USDC actually moves on-chain (after the dispute window).
  const balanceRefreshKey = state.phase === 'closed' ? state.commits.length : 0

  return (
    <div className="min-h-screen flex flex-col">
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
            <div className="min-h-[480px]">
              <OutputPanel
                text={state.accumulated}
                phase={state.phase}
                haltedBy={state.haltedBy}
              />
            </div>
            <TimelinePanel channel={state.channel} commits={state.commits} />
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
