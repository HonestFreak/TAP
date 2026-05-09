// Single-purpose modal: collect the shared access code for hosted demos.
// Stored in localStorage and attached as `X-Tap-Access` by the API client.
// Shown automatically on first visit when the runner has TAP_ACCESS_CODE set.

import { useState, type FormEvent } from 'react'
import { setAccessCode } from '../lib/api'

interface AccessGateProps {
  /** Verifies the code by retrying the auth-gated boot fetch. Returns true
   *  on success (parent will then hide the gate) and false otherwise. */
  onSubmit: () => Promise<boolean>
}

export function AccessGate({ onSubmit }: AccessGateProps) {
  const [value, setValue] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const code = value.trim()
    if (!code) {
      setError('Enter the access code from the submission form.')
      return
    }
    setSubmitting(true)
    setAccessCode(code)
    const ok = await onSubmit()
    setSubmitting(false)
    if (!ok) {
      setError("That code didn't match. Double-check the submission form.")
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-6 shadow-2xl">
        <h2 className="mb-2 text-lg font-semibold">Hosted demo — judges only</h2>
        <p className="mb-3 text-xs leading-relaxed text-[var(--color-text-dim)]">
          Sorry! This hosted demo runs on Solana devnet using a shared
          developer wallet. To prevent abuse, access is gated.
        </p>
        <ul className="mb-4 space-y-2 text-xs leading-relaxed text-[var(--color-text-dim)]">
          <li>
            <strong className="text-[var(--color-text)]">If you're a Frontier judge:</strong>{' '}
            the access code is in the project's Colosseum submission form
            under "access instructions".
          </li>
          <li>
            <strong className="text-[var(--color-text)]">Otherwise:</strong>{' '}
            the protocol is open and MIT-licensed — you can run the same
            demo locally in two commands.{' '}
            <a
              href="https://github.com/HonestFreak/tap"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[var(--color-accent)] underline hover:opacity-80"
            >
              github.com/HonestFreak/tap
            </a>
          </li>
        </ul>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            type="text"
            autoFocus
            autoComplete="off"
            spellCheck={false}
            disabled={submitting}
            value={value}
            onChange={(e) => {
              setValue(e.target.value)
              if (error) setError(null)
            }}
            placeholder="access code"
            className="w-full rounded border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 font-mono text-sm focus:border-[var(--color-accent)] focus:outline-none disabled:opacity-50"
          />
          {error && (
            <div className="text-xs text-[var(--color-danger)]">{error}</div>
          )}
          <button
            type="submit"
            disabled={submitting}
            className="rounded bg-[var(--color-accent)] px-3 py-2 text-sm font-medium text-[var(--color-bg)] transition hover:opacity-90 disabled:opacity-50"
          >
            {submitting ? 'Verifying…' : 'Enter'}
          </button>
        </form>
      </div>
    </div>
  )
}
