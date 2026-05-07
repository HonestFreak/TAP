"""x402 wire format for TAP. Implements the `tap.v1.channel` payment scheme
described in whitepaper §3.3 / Appendix B.1.

The split between this package and `tap.protocol` is deliberate: `protocol`
deals with in-session commitments; `x402` deals only with the HTTP
session-open handshake and is the layer a generic x402-aware client would
encounter."""

from tap.x402.headers import (
    HEADER_PAYMENT,
    HEADER_PAYMENT_REQUIREMENTS,
    HEADER_PAYMENT_RESPONSE,
    HEADER_TAP_COMMIT,
)
from tap.x402.payment import OpenChannelPayment, encode_payment, decode_payment
from tap.x402.requirements import (
    SCHEME,
    PaymentRequirements,
    decode_requirements,
    encode_requirements,
)
from tap.x402.response import PaymentResponse, decode_response, encode_response

__all__ = [
    "HEADER_PAYMENT",
    "HEADER_PAYMENT_REQUIREMENTS",
    "HEADER_PAYMENT_RESPONSE",
    "HEADER_TAP_COMMIT",
    "OpenChannelPayment",
    "PaymentRequirements",
    "PaymentResponse",
    "SCHEME",
    "decode_payment",
    "decode_requirements",
    "decode_response",
    "encode_payment",
    "encode_requirements",
    "encode_response",
]
