/**
 * Error hierarchy for the TAP SDK. All SDK-raised errors subclass `TapError`
 * so callers can catch protocol failures without trapping unrelated network
 * or wallet errors. Mirrors `tap.exceptions` in the Python SDK.
 */

export class TapError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = this.constructor.name;
  }
}

export class X402Error extends TapError {}
export class ProtocolError extends TapError {}
export class CommitmentError extends TapError {}
export class HaltError extends TapError {}
export class SettlementError extends TapError {}
export class ChannelStateError extends TapError {}
