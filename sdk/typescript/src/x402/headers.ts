/**
 * x402 + TAP HTTP header names. One source of truth so hyphens and casing
 * don't drift across the codebase. Mirrors `tap.x402.headers`.
 */

// Defined by the x402 specification.
export const HEADER_PAYMENT_REQUIREMENTS = "X-PAYMENT-REQUIREMENTS";
export const HEADER_PAYMENT = "X-PAYMENT";
export const HEADER_PAYMENT_RESPONSE = "X-PAYMENT-RESPONSE";

// TAP-specific. Distinct from `X-PAYMENT` because in-session commitments are
// signaling, not payment instructions; an x402 facilitator MUST NOT settle
// them.
export const HEADER_TAP_COMMIT = "X-TAP-COMMIT";
export const HEADER_TAP_CHANNEL = "X-TAP-CHANNEL";
export const HEADER_TAP_ACK = "X-TAP-ACK";
