"""Tests for the tokenizer registry and prompt-token verification flow.

The §4.9 input-pricing model relies on the producer and consumer running
the same tokenizer over the same prompt. These tests confirm that:
  1. The default `tap.tok.v1` tokenizer is registered and deterministic.
  2. The `ConsumerPolicy.verify_prompt_tokens` check rejects a producer
     whose declared `input_token_count` disagrees with the local count
     (whitepaper §5.3.7 producer-inflation defense)."""

from __future__ import annotations

import pytest

from tap import tokenizer
from tap.consumer.policy import ConsumerPolicy
from tap.exceptions import X402Error
from tap.x402.requirements import SCHEME, PaymentRequirements


def test_default_tokenizer_registered() -> None:
    assert tokenizer.is_registered("tap.tok.v1")


def test_default_tokenizer_deterministic() -> None:
    text = "Return a JSON object with keys title, summary, tags."
    a = tokenizer.count("tap.tok.v1", text)
    b = tokenizer.count("tap.tok.v1", text)
    assert a == b > 0


def test_unknown_tokenizer_raises() -> None:
    with pytest.raises(KeyError):
        tokenizer.count("does.not.exist", "hi")


def _make_req(*, input_token_count: int, prepaid: int) -> PaymentRequirements:
    return PaymentRequirements(
        scheme=SCHEME,
        network="solana-devnet",
        asset="A",
        recipient="R",
        producer_pubkey="P",
        input_price_micro=1,
        output_price_micro=5,
        max_unpaid_micro=1_000,
        trailing_buffer_tokens=10,
        duration_secs=60,
        dispute_secs=30,
        grace_ms=200,
        pause_timeout_ms=5_000,
        channel_open_url="https://x/open",
        stream_url="https://x/stream",
        tokenizer_id="tap.tok.v1",
        input_token_count=input_token_count,
        prepaid_input_micro=prepaid,
    )


def test_verify_accepts_matching_count() -> None:
    text = "Return a JSON object with keys title, summary, tags."
    expected = tokenizer.count("tap.tok.v1", text)
    req = _make_req(input_token_count=expected, prepaid=expected * 1)
    ConsumerPolicy().verify_prompt_tokens(req, text)


def test_verify_rejects_inflated_count() -> None:
    text = "Hello world."
    expected = tokenizer.count("tap.tok.v1", text)
    req = _make_req(input_token_count=expected + 50, prepaid=(expected + 50) * 1)
    with pytest.raises(X402Error, match="does not match local count"):
        ConsumerPolicy().verify_prompt_tokens(req, text)


def test_audit_rejects_inconsistent_prepaid() -> None:
    # input_token_count × input_price ≠ prepaid_input → X402Error in audit().
    req = _make_req(input_token_count=10, prepaid=999)
    with pytest.raises(X402Error, match="prepaid_input"):
        ConsumerPolicy().audit(req)
