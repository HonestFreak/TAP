// Single-purpose: prompt input + run controls. Owns no session state.

import { useState } from 'react'
import type { SessionPhase } from '../lib/types'

interface Props {
  onRun: (prompt: string, depositMicro: number, enforceSchema: boolean) => void
  onReset: () => void
  phase: SessionPhase
}

const DEFAULT_PROMPT =
  "Return a JSON object with keys `title` (short), `summary` (one sentence), and `tags` (array of 3 keywords). Strictly JSON only — no prose, no code fences."

const HALT_PROMPT =
  "Write me a friendly two-paragraph essay about why summer is the best season. Use lots of words."

export function PromptForm({ onRun, onReset, phase }: Props) {
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT)
  const [deposit, setDeposit] = useState(50_000)
  const [enforceSchema, setEnforceSchema] = useState(true)

  const isRunning = phase === 'opening' || phase === 'streaming'

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-[var(--color-text)]">Prompt</h2>
        <div className="flex gap-2 text-xs">
          <button
            type="button"
            onClick={() => setPrompt(DEFAULT_PROMPT)}
            className="rounded border border-[var(--color-border)] px-2 py-1 text-[var(--color-text-dim)] hover:border-[var(--color-accent)] hover:text-[var(--color-accent)] transition-colors"
          >
            Schema-respecting prompt
          </button>
          <button
            type="button"
            onClick={() => setPrompt(HALT_PROMPT)}
            className="rounded border border-[var(--color-border)] px-2 py-1 text-[var(--color-text-dim)] hover:border-[var(--color-danger)] hover:text-[var(--color-danger)] transition-colors"
          >
            Halt-trigger prompt
          </button>
        </div>
      </div>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        rows={4}
        spellCheck={false}
        className="w-full resize-none rounded-md border border-[var(--color-border)] bg-[var(--color-surface-2)] p-3 font-mono text-sm text-[var(--color-text)] placeholder-[var(--color-text-muted)] focus:border-[var(--color-accent)] focus:outline-none transition-colors"
        placeholder="Ask Gemini something…"
      />
      <div className="mt-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-xs text-[var(--color-text-dim)]">
            <span className="font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
              Deposit
            </span>
            <input
              type="number"
              value={deposit}
              onChange={(e) => setDeposit(Math.max(1_000, Number(e.target.value)))}
              min={1_000}
              step={1_000}
              className="w-24 rounded border border-[var(--color-border)] bg-[var(--color-surface-2)] px-2 py-1 font-mono text-xs text-[var(--color-text)] focus:border-[var(--color-accent)] focus:outline-none"
            />
            <span className="text-[var(--color-text-muted)]">µUSDC</span>
          </label>
          <label className="flex items-center gap-2 text-xs text-[var(--color-text-dim)] cursor-pointer">
            <input
              type="checkbox"
              checked={enforceSchema}
              onChange={(e) => setEnforceSchema(e.target.checked)}
              className="h-3.5 w-3.5 accent-[var(--color-accent)]"
            />
            <span className="font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
              JSON-schema evaluator
            </span>
          </label>
        </div>
        <div className="flex gap-2">
          {phase !== 'idle' && phase !== 'streaming' && phase !== 'opening' && (
            <button
              type="button"
              onClick={onReset}
              className="rounded-md border border-[var(--color-border)] px-3 py-1.5 text-xs text-[var(--color-text-dim)] hover:border-[var(--color-border-strong)] hover:text-[var(--color-text)] transition-colors"
            >
              Reset
            </button>
          )}
          <button
            type="button"
            onClick={() => onRun(prompt, deposit, enforceSchema)}
            disabled={isRunning || !prompt.trim()}
            className="rounded-md bg-[var(--color-accent)] px-4 py-1.5 text-xs font-semibold text-[var(--color-bg)] disabled:cursor-not-allowed disabled:opacity-40 hover:bg-[var(--color-accent)]/90 transition-all"
          >
            {isRunning ? 'Streaming…' : 'Stream response'}
          </button>
        </div>
      </div>
    </div>
  )
}
