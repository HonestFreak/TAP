---
title: TypeScript SDK (consumer)
sidebar_position: 7
---

# TypeScript SDK (consumer)

`@tap-protocol/sdk` is a TypeScript client for the TAP protocol. It is
**consumer-only** by design: producers continue to run the Python SDK at
[`sdk/python/`](/sdk/install) because most LLM serving stacks are Python.
The TypeScript SDK exists so that frontends, Vercel-style edge runtimes, and
agent frameworks built on Node / Bun / Deno can open channels and stream
tokens without leaving JavaScript-land.

Wire format is **byte-for-byte identical** to the Python SDK; cross-language
parity is asserted in
[`sdk/typescript/tests/python-fixtures.test.ts`](https://github.com/HonestFreak/TAP/blob/main/sdk/typescript/tests/python-fixtures.test.ts).
If a Python producer and a TypeScript consumer ever disagree on a wire byte,
that test catches it before anything reaches devnet.

## Install

Not yet published to npm. Install from the repo:

```bash
git clone https://github.com/HonestFreak/TAP
cd TAP/sdk/typescript
npm install
npm run build
```

The package is ESM-only and targets Node 20+ (also Bun, Deno, and modern
browsers — no `node:crypto` dependency).

## Minimal example

```ts
import { TapConsumer, Decision, type Evaluator } from "@tap-protocol/sdk";
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
  depositMicro: 50_000n,           // max session cost: 0.05 USDC
  promptBody,
});

for await (const chunk of session.stream(promptBody)) {
  process.stdout.write(chunk.text);
}

console.log(
  `\nPaid ${session.cumulativePaidMicro} micro-USDC ` +
  `over ${session.tokensReceived} tokens ` +
  `(halted by ${session.haltedBy ?? "completion"})`,
);
```

The flow follows whitepaper §4.9 exactly:

1. **POST the prompt body** to the producer — receives the prompt-bound 402
   quote (`X-PAYMENT-REQUIREMENTS`).
2. **Generate a session keypair** in memory. Your funded wallet doesn't sign
   per-token (whitepaper §4.5).
3. **Build and sign** the `open_channel` transaction with `prepaidInputMicro`
   locked on-chain as the settlement floor.
4. **POST `X-PAYMENT`** carrying the signed tx; receive `X-PAYMENT-RESPONSE`
   with the channel ID.
5. **Stream tokens** over SSE; sign and POST an `X-TAP-COMMIT` every K
   tokens (default K = 8).

## `TapConsumer`

```ts
new TapConsumer({
  wallet,                              // TransactionSigner — pays the deposit
  rpc,                                 // URL string OR Rpc<SolanaRpcApi>
  usdcMint,                            // Address; defaults to devnet USDC
  fetchImpl,                           // optional — defaults to global fetch
});
```

The `wallet` is any `@solana/kit` `TransactionSigner` — typically built with
`createKeyPairSignerFromBytes(...)`. The RPC is used for one call
(`getLatestBlockhash`); the consumer doesn't submit the open-channel tx
itself, it hands the signed bytes to the producer via `X-PAYMENT` and the
producer forwards to the cluster.

### `openSession`

```ts
await consumer.openSession({
  producerUrl: string,
  depositMicro: bigint,
  promptBody: unknown,
  evaluator?: Evaluator,
  commitEveryTokens?: number,        // default 8
  sessionKey?: SessionKey,           // override (testing)
  nonce?: bigint,                    // override (testing)
});
```

Returns a `ConsumerSession`. The `promptBody` you pass here MUST be the
same object you later pass to `session.stream(...)` — the prepaid-input
floor on the channel is bound to this prompt's tokenization.

## `ConsumerSession`

The object returned by `openSession`. One session per request.

### Streaming

`session.stream(body)` is an async iterator yielding `TokenChunk`s:

```ts
interface TokenChunk {
  readonly text: string;
  readonly cumulativePaidMicro: bigint;
  readonly tokensReceived: number;
}
```

The session internally:

* Accumulates output and runs the evaluator after each token.
* Signs an `X-TAP-COMMIT` every K tokens (K is fixed in the TS MVP; the
  Python SDK adapts K via AIMD on producer pressure).
* Halts the stream and force-signs a final commit if the evaluator returns
  `Decision.HALT`.

### Properties

| Property | Type | Description |
| --- | --- | --- |
| `channelId` | `Address` | Base58 channel PDA |
| `sessionPublicKey` | `Address` | The in-memory session-key pubkey registered on-chain |
| `openTxSignature` | `string \| null` | Signature of the `open_channel` transaction |
| `cumulativePaidMicro` | `bigint` | Latest `cumulative_paid` the consumer has signed |
| `tokensReceived` | `number` | Output tokens streamed so far |
| `haltedBy` | `string \| null` | Name of the evaluator that halted the session, if any |

## Halt-on-evaluator

Any function `(accumulated: string) => Decision` is an evaluator:

```ts
import { Decision, type Evaluator } from "@tap-protocol/sdk";

const lengthCap: Evaluator = (text) =>
  text.length >= 2_000 ? Decision.HALT : Decision.CONTINUE;
(lengthCap as { name?: string }).name = "length_cap(2000)";

const session = await consumer.openSession({
  producerUrl, depositMicro: 50_000n, promptBody,
  evaluator: lengthCap,
});
```

Set `.name` on the callable so `session.haltedBy` surfaces a meaningful
identifier. See the Python [Evaluators](/sdk/evaluators) page for the full
catalogue (JSON schema, topic drift, repetition guard, content policy) —
porting them to TS is a mechanical translation and a fine first
contribution.

## Public surface

```ts
// Consumer client + session
export { TapConsumer, ConsumerSession, Decision };
export type { Evaluator, TokenChunk, OpenSessionArgs, TapConsumerInit };
export { generateSessionKey, sessionKeyFromSeed, type SessionKey };

// Protocol layer — for custom integrations
export type { CommitMessage, SignedCommitment };
export { COMMIT_SCHEMA, encodeCommitment, decodeCommitment, encodeCommitmentBytes };
export { signCommitment, verifyCommitment };

// x402 codecs
export { X402_SCHEME, encodeRequirements, decodeRequirements };
export type { PaymentRequirements };
export { encodePayment, decodePayment, type OpenChannelPayment };
export { encodeResponse, decodeResponse, type PaymentResponse };
export * as headers from "./x402/headers.js";

// Chain layer
export { PROGRAM_ID, USDC_MINT_DEVNET, USDC_MINT_MAINNET };
export { deriveChannelPda, deriveVaultPda, deriveAta };
export { buildOpenChannelInstruction };

// Exceptions — all subclass TapError
export {
  TapError, X402Error, ProtocolError, CommitmentError,
  HaltError, SettlementError, ChannelStateError,
};
```

## Wire-format parity with Python

The TS SDK encodes wire bytes identically to the Python SDK. Specifically:

* **Commit byte layout** (signed and on-chain verified): 32 channel + 8 seq
  + 8 paid + 4 tokens + 8 ts = 60 bytes, little-endian. Identical to
  `sdk/python/tap/protocol/codec.py`.
* **Header JSON** (`X-PAYMENT*`, `X-TAP-COMMIT`): base64 of a JSON object
  with the same field names, ordering, and numeric typing as the Python
  encoder. Numeric fields are JSON numbers (not strings) so the
  base64-encoded bytes match.
* **PDA seeds**: `tap-channel` + consumer + producer + nonce(u64 LE);
  `tap-vault` + channel. Identical to
  [`programs/tap/src/constants.rs`](/protocol/on-chain).

The parity test in
[`tests/python-fixtures.test.ts`](https://github.com/HonestFreak/TAP/blob/main/sdk/typescript/tests/python-fixtures.test.ts)
asserts byte-for-byte equivalence against base64 strings captured from the
Python encoder; regenerate them with:

```bash
python3 sdk/typescript/scripts/dump_fixtures.py
```

## Wire-format gotcha: u64 nonces

The on-chain channel PDA is seeded with a `u64` nonce, but the x402
payload transports it as a JSON number. JavaScript can only represent
integers losslessly up to `2^53 − 1`. The TS SDK therefore generates
nonces capped at `2^53 − 1`:

```ts
function randomNonce(): bigint {
  const bytes = new Uint8Array(8);
  crypto.getRandomValues(bytes);
  bytes[7] = 0;
  bytes[6] = bytes[6]! & 0x1f;
  return new DataView(bytes.buffer).getBigUint64(0, true);
}
```

The on-chain seed width is unchanged (high bits are just zero). If a Python
producer ever returned a nonce above `2^53` over the wire, JavaScript would
lose precision on parse — but the TS consumer generates the nonce itself,
so this only matters if you ever decode a Python-emitted `X-PAYMENT` from
TS. The collision space at 53 bits is still cosmic.

## Deferred from parity

The TS SDK ships as a consumer MVP. The following are present in the
Python SDK and **not yet** ported — they are additive on top of the wire
format and can be filled in without breaking it:

| Feature | Status | Where to add |
| --- | --- | --- |
| Local prompt re-tokenization (whitepaper §5.3.7) | Deferred | New `src/tokenizer.ts` mirroring `tap.tokenizer` |
| `ConsumerPolicy` audit of producer terms | Deferred | New `src/consumer/policy.ts` |
| AIMD adaptive commit batching | Deferred — fixed K | `src/consumer/session.ts` |
| `HaltDetector` pause/halt timeouts | Deferred — relies on `fetch` timeout | `src/consumer/session.ts` |
| Built-in evaluators (json_schema, length_cap, …) | Deferred | New `src/evaluators/*.ts` |
| Producer host (`TapProducer`) | Not planned — use Python | — |
| Settler + model adapters | Not planned — use Python | — |

## Tests

```bash
cd sdk/typescript
npm test
```

Runs all suites under `tests/`:

| Suite | What it covers |
| --- | --- |
| `codec.test.ts` | Byte layout, header round-trip, sign/verify |
| `pda.test.ts` | Channel/vault PDA determinism + seed strings |
| `x402.test.ts` | Round-trip for all three x402 codecs |
| `python-fixtures.test.ts` | Byte-for-byte parity with Python fixtures |

19 tests total. CI-friendly via Node's built-in `node:test` runner — no
extra dev dependencies beyond `typescript`.
