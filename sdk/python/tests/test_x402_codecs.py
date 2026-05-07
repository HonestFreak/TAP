"""Round-trip tests for the x402 wire codecs."""

from __future__ import annotations

from tap.x402.payment import OpenChannelPayment, decode_payment, encode_payment
from tap.x402.requirements import (
    SCHEME,
    PaymentRequirements,
    decode_requirements,
    encode_requirements,
)
from tap.x402.response import PaymentResponse, decode_response, encode_response


def test_requirements_round_trip() -> None:
    req = PaymentRequirements(
        scheme=SCHEME,
        network="solana-devnet",
        asset="4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",
        recipient="TapPRoTuQDmXiBg2H4Z7Lp4uKnxw3w6f8Y4F2X1aBcD",
        producer_pubkey="prod1111111111111111111111111111111111111111",
        input_price_micro=1,
        output_price_micro=5,
        max_unpaid_micro=1_000,
        trailing_buffer_tokens=10,
        duration_secs=600,
        dispute_secs=30,
        grace_ms=200,
        pause_timeout_ms=5_000,
        channel_open_url="https://x/open",
        stream_url="https://x/stream",
        tokenizer_id="tap.tok.v1",
        input_token_count=42,
        prepaid_input_micro=42,
        model="claude-sonnet-4-6",
    )
    assert decode_requirements(encode_requirements(req)) == req


def test_payment_round_trip() -> None:
    payment = OpenChannelPayment(
        scheme=SCHEME,
        network="solana-devnet",
        consumer_pubkey="cons111111111111111111111111111111111111111",
        session_key="sess111111111111111111111111111111111111111",
        nonce=42,
        deposit_micro=50_000,
        input_price_micro=1,
        output_price_micro=5,
        prepaid_input_micro=200,
        duration_secs=600,
        dispute_secs=30,
        trailing_buffer_tokens=10,
        transaction_b64="AA==",
    )
    assert decode_payment(encode_payment(payment)) == payment


def test_response_round_trip() -> None:
    resp = PaymentResponse(
        tx_hash="sig",
        settlement="confirmed",
        channel_id="chan",
        channel_state="active",
    )
    assert decode_response(encode_response(resp)) == resp
