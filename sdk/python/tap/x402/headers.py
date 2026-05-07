"""x402 + TAP HTTP header names. One source of truth so hyphens and casing
don't drift across the codebase."""

from __future__ import annotations

# Defined by the x402 specification.
HEADER_PAYMENT_REQUIREMENTS = "X-PAYMENT-REQUIREMENTS"
HEADER_PAYMENT = "X-PAYMENT"
HEADER_PAYMENT_RESPONSE = "X-PAYMENT-RESPONSE"

# TAP-specific. Distinct from `X-PAYMENT` because in-session commitments are
# signaling, not payment instructions; an x402 facilitator MUST NOT settle
# them.
HEADER_TAP_COMMIT = "X-TAP-COMMIT"
HEADER_TAP_ACK = "X-TAP-ACK"
