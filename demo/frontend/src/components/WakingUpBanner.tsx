// Non-blocking banner shown when a session start hangs in the 'opening'
// phase longer than expected. The runner is warm by this point (we just
// authed against it) but the producer it calls might be cold-starting on
// free hosting; rather than freezing the UI, surface a small explainer.

interface WakingUpBannerProps {
  visible: boolean
}

export function WakingUpBanner({ visible }: WakingUpBannerProps) {
  if (!visible) return null
  return (
    <div className="flex items-center gap-3 rounded border border-[var(--color-accent)]/30 bg-[var(--color-accent)]/10 px-4 py-3 text-xs text-[var(--color-text-dim)]">
      <div className="h-3 w-3 shrink-0 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-accent)]" />
      <span>
        <strong className="text-[var(--color-text)]">Waking the producer.</strong>{' '}
        Hosted on free-tier infrastructure — the first session after idle
        takes about 30 seconds. Subsequent ones stream instantly.
      </span>
    </div>
  )
}
