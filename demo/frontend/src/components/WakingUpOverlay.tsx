// Single-purpose: tell the user the demo server is cold-starting.
// Render's free/Starter plans sleep after idle; the first request takes
// ~30s. Without this overlay the dashboard just looks frozen.

interface WakingUpOverlayProps {
  visible: boolean
}

export function WakingUpOverlay({ visible }: WakingUpOverlayProps) {
  if (!visible) return null
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/70 px-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-6 text-center shadow-2xl">
        <div className="mb-4 flex justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-accent)]" />
        </div>
        <h2 className="mb-1 text-lg font-semibold">Waking the server</h2>
        <p className="text-xs text-[var(--color-text-dim)]">
          Hosted on free-tier infrastructure. The first request after idle
          takes about 30 seconds — subsequent ones are instant.
        </p>
        <p className="mt-3 text-[11px] text-[var(--color-text-muted)]">
          Hang tight. We'll continue automatically once it's up.
        </p>
      </div>
    </div>
  )
}
