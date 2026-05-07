import React, {useEffect, useRef, useState} from 'react';
import styles from './MeterDemo.module.css';

const SCRIPTED_TOKENS = [
  'Sure, ', 'here ', 'is ', 'the ', 'JSON ', 'object ', 'you ', 'requested:\n',
  '{\n  ', '"title": ', '"Quarterly ', 'sales ', 'report",\n  ',
  '"summary": ', '"Revenue ', 'grew ', '12%', ' YoY, ', 'driven ', 'by ',
  'the ', 'enterprise ', 'segment.",\n  ', '"tags": ',
  '["sales", ', '"q3", ', '"enterprise"]\n}',
];

const ROGUE_TOKENS = [
  'Sure, ', 'here ', 'is ', 'the ', 'JSON ', 'object ', 'you ', 'requested:\n',
  'Actually, ', 'let ', 'me ', 'tell ', 'you ', 'a ', 'long ', 'story ',
  'first ', 'about ', 'the ', 'history ', 'of ', 'quarterly ', 'reports ',
  'in ', 'the ', 'industrial ', 'revolution ', '— ', 'it ', 'all ', 'began ',
  'in ', 'the ', '18th ', 'century ', 'when ', 'merchants ', '…',
];

type Mode = 'good' | 'rogue';

const OUTPUT_PRICE_MICRO = 5; // 0.000005 USDC per output token (matches demo)
const PREPAID_INPUT_MICRO = 12;

export default function MeterDemo(): JSX.Element {
  const [mode, setMode] = useState<Mode>('rogue');
  const [running, setRunning] = useState(false);
  const [text, setText] = useState('');
  const [tokens, setTokens] = useState(0);
  const [paidMicro, setPaidMicro] = useState(0);
  const [halted, setHalted] = useState<string | null>(null);
  const [completed, setCompleted] = useState(false);
  const cancelRef = useRef(false);

  const script = mode === 'good' ? SCRIPTED_TOKENS : ROGUE_TOKENS;
  const haltAt = mode === 'rogue' ? 9 : null; // halt right when "Actually, " arrives
  const total = script.length;

  function reset() {
    cancelRef.current = true;
    setText('');
    setTokens(0);
    setPaidMicro(0);
    setHalted(null);
    setCompleted(false);
    setRunning(false);
  }

  async function start() {
    cancelRef.current = false;
    setText('');
    setTokens(0);
    setPaidMicro(PREPAID_INPUT_MICRO);
    setHalted(null);
    setCompleted(false);
    setRunning(true);

    for (let i = 0; i < script.length; i++) {
      if (cancelRef.current) return;
      await sleep(120);
      if (cancelRef.current) return;
      setText((prev) => prev + script[i]);
      setTokens(i + 1);
      setPaidMicro((prev) => prev + OUTPUT_PRICE_MICRO);

      if (haltAt !== null && i + 1 === haltAt) {
        await sleep(220); // "evaluator runs ~50–200ms"
        if (cancelRef.current) return;
        setHalted('json_schema (off-topic prefix)');
        setRunning(false);
        return;
      }
    }
    setCompleted(true);
    setRunning(false);
  }

  useEffect(() => () => { cancelRef.current = true; }, []);

  const fillPercent = Math.min(100, (tokens / total) * 100);
  const refundMicro = haltAt
    ? Math.max(0, (total - tokens) * OUTPUT_PRICE_MICRO)
    : 0;

  return (
    <section className={styles.wrap}>
      <div className={styles.head}>
        <h2 className={styles.h2}>
          See it in action
        </h2>
        <p className={styles.sub}>
          A consumer asks for JSON. The producer streams tokens; the consumer
          signs incremental commitments. When the model goes off-topic, the
          evaluator halts the stream — and the unspent deposit refunds on-chain.
        </p>
      </div>

      <div className={styles.toggle} role="tablist" aria-label="Demo mode">
        <button
          role="tab"
          aria-selected={mode === 'rogue'}
          className={mode === 'rogue' ? styles.toggleActive : styles.toggleBtn}
          onClick={() => { reset(); setMode('rogue'); }}
        >
          Off-topic response (halt)
        </button>
        <button
          role="tab"
          aria-selected={mode === 'good'}
          className={mode === 'good' ? styles.toggleActive : styles.toggleBtn}
          onClick={() => { reset(); setMode('good'); }}
        >
          Valid response (run to completion)
        </button>
      </div>

      <div className={styles.grid}>
        <div className={styles.terminal}>
          <div className={styles.terminalHead}>
            <span className={styles.dot} style={{background: '#ff5f57'}} />
            <span className={styles.dot} style={{background: '#febc2e'}} />
            <span className={styles.dot} style={{background: '#28c840'}} />
            <span className={styles.terminalTitle}>session.stream(prompt)</span>
          </div>
          <pre className={styles.terminalBody}>
            <code>{text || <span className={styles.placeholder}>// click Start to stream tokens</span>}</code>
            {running && <span className={styles.cursor}>▍</span>}
          </pre>
        </div>

        <div className={styles.meter}>
          <div className={styles.meterRow}>
            <span className={styles.meterLabel}>Tokens received</span>
            <span className={styles.meterValue}>{tokens}<span className={styles.meterSuffix}>/{total}</span></span>
          </div>
          <div className={styles.bar}>
            <div className={styles.barFill} style={{width: `${fillPercent}%`}} />
          </div>

          <div className={styles.meterRow}>
            <span className={styles.meterLabel}>Cumulative paid</span>
            <span className={styles.meterValueGreen}>
              ${formatUsdc(paidMicro)}
            </span>
          </div>
          <div className={styles.meterRow}>
            <span className={styles.meterLabel}>Prepaid input floor</span>
            <span className={styles.meterValueDim}>${formatUsdc(PREPAID_INPUT_MICRO)}</span>
          </div>
          <div className={styles.meterRow}>
            <span className={styles.meterLabel}>Refund pending settlement</span>
            <span className={styles.meterValueDim}>${formatUsdc(refundMicro)}</span>
          </div>

          <div className={styles.statusBlock}>
            {halted && (
              <div className={styles.statusHalt}>
                <strong>Evaluator halt:</strong> {halted}
                <div className={styles.statusSub}>
                  Final commit force-signed at token {tokens}. Producer settles
                  on-chain with cumulative_paid = ${formatUsdc(paidMicro)}.
                </div>
              </div>
            )}
            {completed && (
              <div className={styles.statusOk}>
                <strong>Stream complete.</strong> Final commit at token {tokens}.
                Cumulative paid = ${formatUsdc(paidMicro)}.
              </div>
            )}
            {!halted && !completed && (
              <div className={styles.statusIdle}>
                {running
                  ? 'Streaming · signing X-TAP-COMMIT every K tokens'
                  : 'Idle · channel open, deposit escrowed, evaluator armed'}
              </div>
            )}
          </div>

          <div className={styles.ctaRow}>
            <button
              className={styles.primary}
              onClick={start}
              disabled={running}
            >
              {running ? 'Streaming…' : 'Start session'}
            </button>
            <button
              className={styles.secondary}
              onClick={reset}
              disabled={!running && !text}
            >
              Reset
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

function sleep(ms: number) {
  return new Promise((res) => setTimeout(res, ms));
}

function formatUsdc(micro: number): string {
  return (micro / 1_000_000).toFixed(6);
}
