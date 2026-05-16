# `@tap-protocol/sdk`

TypeScript consumer SDK for the TAP (Token Access Protocol) — token-by-token
payments for LLM inference on Solana.

Mirrors the wire format of the Python SDK at [`../python/`](../python/);
cross-language parity is verified in [`tests/python-fixtures.test.ts`](tests/python-fixtures.test.ts)
against base64 fixtures captured from the Python encoder.

> **Scope.** This SDK ships the **consumer** side (open a channel, stream
> tokens, sign commitments, halt). Producers should continue to run the
> Python SDK at `sdk/python/` — most LLM serving is Python anyway, and the
> reference demo at `demo/` (which the TS SDK does not touch) is the
> end-to-end story.

## Install

Not yet published. Install editable from a clone:

```bash
git clone https://github.com/HonestFreak/TAP
cd TAP/sdk/typescript
npm install
npm run build
```

## Consumer

```ts
import {
  TapConsumer,
  Decision,
  type Evaluator,
} from "@tap-protocol/sdk";
import {
  createKeyPairSignerFromBytes,
  createSolanaRpc,
} from "@solana/kit";

const wallet = await createKeyPairSignerFromBytes(loadConsumerSecretKey());
const consumer = new TapConsumer({
  wallet,
  rpc: createSolanaRpc("https://api.devnet.solana.com"),
});

const promptBody = {
  messages: [
    { role: "user", content: "Return JSON: {title, summary, tags[]}." },
  ],
};

const session = await consumer.openSession({
  producerUrl: "https://provider.example.com/v1/messages",
  depositMicro: 50_000n,           // 0.05 USDC max
  promptBody,
});

for await (const chunk of session.stream(promptBody)) {
  process.stdout.write(chunk.text);
}
console.log(
  `\nPaid ${session.cumulativePaidMicro} micro-USDC over ${session.tokensReceived} tokens`,
);
```

### Halt on evaluator

Any function `(accumulated: string) => "CONTINUE" | "HALT"` works:

```ts
const lengthCap: Evaluator = (text) =>
  text.length >= 2_000 ? Decision.HALT : Decision.CONTINUE;
(lengthCap as { name?: string }).name = "length_cap(2000)";

const session = await consumer.openSession({
  producerUrl, depositMicro: 50_000n, promptBody, evaluator: lengthCap,
});
```

`session.haltedBy` surfaces the evaluator's `name` after the iterator ends.

## Layout

One responsibility per file, mirroring the Python package.

| Module | Purpose |
|---|---|
| `src/protocol/commit.ts` | `CommitMessage` + `SignedCommitment` types |
| `src/protocol/codec.ts` | Canonical byte + JSON encodings for commits |
| `src/protocol/signing.ts` | Ed25519 sign/verify over `encodeCommitmentBytes` |
| `src/x402/requirements.ts` | `X-PAYMENT-REQUIREMENTS` codec |
| `src/x402/payment.ts` | `X-PAYMENT` codec |
| `src/x402/response.ts` | `X-PAYMENT-RESPONSE` codec |
| `src/x402/headers.ts` | HTTP header name constants |
| `src/chain/programId.ts` | Program + mint addresses |
| `src/chain/discriminator.ts` | Anchor 8-byte discriminators |
| `src/chain/pda.ts` | Channel/vault PDA + ATA derivation |
| `src/chain/openChannelInstruction.ts` | `open_channel` ix builder |
| `src/consumer/client.ts` | `TapConsumer` — top-level entry point |
| `src/consumer/session.ts` | `ConsumerSession` — streaming + commit signing |
| `src/consumer/sessionKey.ts` | Ephemeral Ed25519 session keypair |
| `src/consumer/discovery.ts` | Prompt-bound 402 fetch |
| `src/consumer/openChannelTx.ts` | Build + sign the channel-open tx |
| `src/consumer/sse.ts` | Minimal `text/event-stream` parser |

## Wire-format guarantees

* **Commit byte layout** (signed and on-chain verified): 32 + 8 + 8 + 4 + 8
  bytes, little-endian. Identical to `sdk/python/tap/protocol/codec.py`.
* **Header JSON** (`X-PAYMENT*`, `X-TAP-COMMIT`): base64 of a JSON object with
  the same field names, ordering, and numeric typing as the Python encoder.
  Numeric fields are JSON numbers (not strings) for byte-for-byte parity.
* **PDA seeds**: `b"tap-channel"` + consumer + producer + nonce(LE u64);
  `b"tap-vault"` + channel. Identical to Anchor `programs/tap/src/constants.rs`.

## Differences from the Python SDK

Deferred to a future iteration (out of scope for the consumer MVP):

* **Local prompt tokenization** (whitepaper §5.3.7 input-inflation defense).
  Producer's `inputTokenCount` is trusted; verification would need a
  tokenizer registry equivalent to `tap.tokenizer`.
* **`ConsumerPolicy` audit** of producer terms before escrow.
* **AIMD adaptive batching** — `commitEveryTokens` is fixed (default 8).
* **`HaltDetector` pause/halt timeouts** — relies on the underlying `fetch`
  stream timing out.
* **Producer host, settler, model adapters** — Python-only for now.

## Tests

```bash
npm test
```

Runs all suites under `tests/`, including byte-for-byte parity with Python
fixtures captured from `sdk/python/tap/...`.
