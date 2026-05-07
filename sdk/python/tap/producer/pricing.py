"""Producer pricing parameters.

Single immutable struct so handlers don't take a long argument list and
configuration changes are visible at one site. Pricing is split per
whitepaper §4.8: input is charged once at channel open as `prepaid_input`
(= `input_token_count × input_price_micro`); output is charged
incrementally as it streams. The asymmetry reflects real-world LLM
economics where output costs typically 3-5x as much as input."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Pricing:
    """All pricing-related parameters in one place."""

    input_price_micro: int
    """Price per prompt (input) token, micro-USDC. Charged once at open."""

    output_price_micro: int
    """Price per generated (output) token, micro-USDC. Charged per token."""

    max_unpaid_micro: int
    """Maximum value the producer will deliver before halting if no
    commitment arrives covering it. Bounds producer-side exposure."""

    trailing_buffer_tokens: int
    """Tokens of trailing output buffer pre-authorized at channel open
    (whitepaper §4.6). Applies to output streaming only — input cost is
    already secured by `prepaid_input`."""

    tokenizer_id: str
    """Identifier for the tokenizer the producer uses to count prompt
    tokens at the 402 response (whitepaper §4.9). Must be registered with
    `tap.tokenizer.register` before the server starts; the consumer SHOULD
    re-tokenize locally with the same id (whitepaper §5.3.7)."""

    min_deposit_micro: int = 1_000   # 0.001 USDC
    max_deposit_micro: int = 1_000_000_000  # 1,000 USDC

    def __post_init__(self) -> None:
        if self.input_price_micro <= 0:
            raise ValueError("input_price_micro must be positive")
        if self.output_price_micro <= 0:
            raise ValueError("output_price_micro must be positive")
        if self.max_unpaid_micro <= 0:
            raise ValueError("max_unpaid_micro must be positive")
        if self.trailing_buffer_tokens < 0:
            raise ValueError("trailing_buffer_tokens must be non-negative")
        if self.min_deposit_micro > self.max_deposit_micro:
            raise ValueError("min_deposit_micro must be <= max_deposit_micro")
        if not self.tokenizer_id:
            raise ValueError("tokenizer_id must be a non-empty identifier")
