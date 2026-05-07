import React, {useEffect, useState} from 'react';
import styles from './FlowHeroVisual.module.css';

/**
 * Autoplay hero animation: tokens flow through a pipe, an evaluator pulse
 * fires, the valve closes, the flow halts, then resumes. Loops forever.
 *
 * This is the protocol's pitch in one visual. The MeterDemo below lets the
 * user trigger the same gesture themselves — the hero teaches it.
 */

type Phase = 'flowing' | 'halting' | 'halted' | 'resuming';

const PHASES: ReadonlyArray<{name: Phase; duration: number}> = [
  {name: 'flowing',  duration: 5200},
  {name: 'halting',  duration: 600},
  {name: 'halted',   duration: 2400},
  {name: 'resuming', duration: 600},
];

// Token shapes that look like actual LLM output fragments.
const TOKEN_GLYPHS = [
  'Sure', ',', ' here', ' is', ' the', ' JSON', ':', ' ',
  '{', '"id"', ':', ' 42', ',', ' "ok"', ':', ' true', '}',
  ' /*', ' next', ' chunk', ' */',
  ' "', 'q3', '"', ',', ' "', 'sales', '"',
];

export default function FlowHeroVisual(): JSX.Element {
  const [phaseIdx, setPhaseIdx] = useState(0);
  const phase = PHASES[phaseIdx].name;

  useEffect(() => {
    const t = setTimeout(() => {
      setPhaseIdx((i) => (i + 1) % PHASES.length);
    }, PHASES[phaseIdx].duration);
    return () => clearTimeout(t);
  }, [phaseIdx]);

  const valveClosed = phase === 'halted' || phase === 'halting';

  return (
    <div className={styles.scene} data-phase={phase} aria-hidden="true">
      <div className={styles.rail}>
        <div className={styles.railWall} />

        {/* Two copies of the token row, one after the other, scrolling
            leftward. When halted, the animation pauses. */}
        <div className={styles.streamWindow}>
          <div className={styles.streamTrack} data-phase={phase}>
            <TokenRow />
            <TokenRow />
          </div>
        </div>

        {/* Halt marker — vertical amber line at the valve position. */}
        <div className={styles.haltMark} data-phase={phase} />

        {/* Valve sits at ~78% across — flow visibly cuts off when it closes. */}
        <div className={styles.valveSlot}>
          <Valve closed={valveClosed} phase={phase} />
        </div>
      </div>

      <Caption phase={phase} />
    </div>
  );
}

function TokenRow() {
  return (
    <div className={styles.tokenRow}>
      {TOKEN_GLYPHS.map((g, i) => (
        <span key={i} className={styles.tokenPill}>{g}</span>
      ))}
    </div>
  );
}

function Valve({closed, phase}: {closed: boolean; phase: Phase}) {
  return (
    <svg viewBox="0 0 64 64" className={styles.valve} data-phase={phase}>
      <circle cx="32" cy="32" r="28" className={styles.valveBody} />
      <circle cx="32" cy="32" r="28" className={styles.valveRing} />
      <line
        x1="6" y1="32" x2="58" y2="32"
        className={styles.valveDisc}
        style={{transform: closed ? 'rotate(90deg)' : 'rotate(0deg)'}}
      />
      <circle cx="32" cy="32" r="4" className={styles.valveHub} />
    </svg>
  );
}

function Caption({phase}: {phase: Phase}) {
  const text =
    phase === 'flowing'  ? 'STREAMING · X-TAP-COMMIT every K tokens'
  : phase === 'halting'  ? 'EVALUATOR PULSE · closing the tap'
  : phase === 'halted'   ? 'HALTED · final commit signed, refund pending'
  :                        'OPENING · channel re-armed';
  return (
    <div className={styles.caption} data-phase={phase}>
      <span className={styles.captionDot} data-phase={phase} />
      <span className={styles.captionText}>{text}</span>
    </div>
  );
}
