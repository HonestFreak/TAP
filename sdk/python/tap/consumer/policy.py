"""Consumer-side policy audit of producer-published `PaymentRequirements`
(whitepaper §4.8).

A consumer's runtime can be configured to refuse channels with terms it
considers unfavorable. By failing fast at discovery time, we ensure that
no funds are ever escrowed against terms the consumer would not accept.

The policy also handles the §5.3.7 input-inflation defense: if the consumer
has registered the producer's declared tokenizer locally, it re-tokenizes
the prompt and checks the producer's `input_token_count` against the
local count. A mismatch implies misbehaviour (tokenizers are deterministic)
and aborts the open."""

from __future__ import annotations

from dataclasses import dataclass

from tap import tokenizer
from tap.exceptions import X402Error
from tap.x402.requirements import PaymentRequirements


@dataclass(frozen=True, slots=True)
class ConsumerPolicy:
    max_input_price_micro: int = 100   # 0.0001 USDC per prompt token
    max_output_price_micro: int = 200  # 0.0002 USDC per generated token
    max_trailing_buffer_tokens: int = 32
    min_pause_timeout_ms: int = 500
    max_dispute_secs: int = 300
    allowed_networks: frozenset[str] = frozenset({"solana-devnet", "solana-mainnet"})
    verify_input_tokens: bool = True
    """When True (default), re-tokenize the prompt locally with the producer's
    declared tokenizer and abort if the count disagrees (whitepaper §5.3.7).
    Set False for low-stakes sessions or when no local tokenizer is available."""

    def audit(self, req: PaymentRequirements) -> None:
        if req.network not in self.allowed_networks:
            raise X402Error(f"network {req.network!r} not in allowed set")
        if req.input_price_micro > self.max_input_price_micro:
            raise X402Error(
                f"input price {req.input_price_micro} exceeds policy max "
                f"{self.max_input_price_micro}"
            )
        if req.output_price_micro > self.max_output_price_micro:
            raise X402Error(
                f"output price {req.output_price_micro} exceeds policy max "
                f"{self.max_output_price_micro}"
            )
        if req.trailing_buffer_tokens > self.max_trailing_buffer_tokens:
            raise X402Error(
                f"trailing buffer {req.trailing_buffer_tokens} exceeds policy max "
                f"{self.max_trailing_buffer_tokens}"
            )
        if req.pause_timeout_ms < self.min_pause_timeout_ms:
            raise X402Error(
                f"pause timeout {req.pause_timeout_ms}ms below policy min "
                f"{self.min_pause_timeout_ms}ms"
            )
        if req.dispute_secs > self.max_dispute_secs:
            raise X402Error(
                f"dispute window {req.dispute_secs}s exceeds policy max "
                f"{self.max_dispute_secs}s"
            )
        # Internal consistency: prepaid_input the producer claims must match
        # input_token_count × input_price_micro. Producers cannot smuggle
        # extra cost into prepaid_input without it showing up here.
        expected_prepaid = req.input_token_count * req.input_price_micro
        if req.prepaid_input_micro != expected_prepaid:
            raise X402Error(
                f"prepaid_input {req.prepaid_input_micro} does not match "
                f"input_token_count × input_price ({expected_prepaid})"
            )

    def verify_prompt_tokens(self, req: PaymentRequirements, prompt_text: str) -> None:
        """Re-tokenize `prompt_text` locally and check against the producer's
        count. Whitepaper §5.3.7: tokenizers are deterministic, so honest
        disagreement is impossible — any mismatch is misbehaviour and the
        consumer aborts before any funds escrow."""
        if not self.verify_input_tokens:
            return
        if req.input_token_count == 0:
            # Generic 402 with no prompt-bound quote; nothing to verify.
            return
        if not tokenizer.is_registered(req.tokenizer_id):
            raise X402Error(
                f"producer declared tokenizer {req.tokenizer_id!r} which is "
                "not registered locally; cannot verify input_token_count"
            )
        local = tokenizer.count(req.tokenizer_id, prompt_text)
        if local != req.input_token_count:
            raise X402Error(
                f"producer's input_token_count {req.input_token_count} does "
                f"not match local count {local} for tokenizer "
                f"{req.tokenizer_id!r}"
            )
