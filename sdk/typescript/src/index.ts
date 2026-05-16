/**
 * TAP — Token Access Protocol. TypeScript consumer SDK.
 *
 * Public surface. Anything not re-exported here is an implementation detail
 * and may move between releases. Mirrors `sdk/python/tap/__init__.py`.
 */

export { TapConsumer, type OpenSessionArgs, type TapConsumerInit } from "./consumer/client.js";
export {
  ConsumerSession,
  Decision,
  type Evaluator,
  type TokenChunk,
} from "./consumer/session.js";
export { generateSessionKey, sessionKeyFromSeed, type SessionKey } from "./consumer/sessionKey.js";

// Protocol layer — exposed for custom integrations.
export type { CommitMessage, SignedCommitment } from "./protocol/commit.js";
export { SCHEMA as COMMIT_SCHEMA } from "./protocol/commit.js";
export {
  encodeCommitment,
  decodeCommitment,
  encodeCommitmentBytes,
} from "./protocol/codec.js";
export { signCommitment, verifyCommitment } from "./protocol/signing.js";

// x402 wire codecs.
export {
  SCHEME as X402_SCHEME,
  type PaymentRequirements,
  encodeRequirements,
  decodeRequirements,
} from "./x402/requirements.js";
export {
  type OpenChannelPayment,
  encodePayment,
  decodePayment,
} from "./x402/payment.js";
export {
  type PaymentResponse,
  encodeResponse,
  decodeResponse,
} from "./x402/response.js";
export * as headers from "./x402/headers.js";

// Chain layer.
export {
  PROGRAM_ID,
  USDC_MINT_DEVNET,
  USDC_MINT_MAINNET,
} from "./chain/programId.js";
export { deriveChannelPda, deriveVaultPda, deriveAta } from "./chain/pda.js";
export {
  buildOpenChannelInstruction,
  type OpenChannelArgs,
  type OpenChannelInstruction,
} from "./chain/openChannelInstruction.js";

// Exceptions.
export {
  TapError,
  X402Error,
  ProtocolError,
  CommitmentError,
  HaltError,
  SettlementError,
  ChannelStateError,
} from "./exceptions.js";
