"""Smoke tests for the bundled evaluators."""

from __future__ import annotations

from tap.evaluators.base import Decision
from tap.evaluators.compose import compose
from tap.evaluators.content_policy import content_policy
from tap.evaluators.json_schema import json_schema
from tap.evaluators.length_cap import length_cap
from tap.evaluators.repetition import repetition_guard
from tap.evaluators.topic_drift import topic_drift


def test_length_cap() -> None:
    e = length_cap(10)
    assert e("12345") is Decision.CONTINUE
    assert e("12345678901") is Decision.HALT


def test_json_schema_halts_on_invalid_first_char() -> None:
    e = json_schema({"type": "object"})
    assert e("hello") is Decision.HALT
    assert e("{\"a\": 1") is Decision.CONTINUE  # incomplete; not yet decisive


def test_content_policy() -> None:
    e = content_policy(["secret"])
    assert e("nothing here") is Decision.CONTINUE
    assert e("the SECRET is out") is Decision.HALT


def test_topic_drift_short_circuits_for_short_input() -> None:
    e = topic_drift("solana payments", min_chars=200)
    assert e("anything short") is Decision.CONTINUE


def test_repetition_guard_flags_loop() -> None:
    e = repetition_guard(window=64, threshold=0.4)
    assert e("AAAAAAAA" * 16) is Decision.HALT


def test_compose_short_circuits() -> None:
    e = compose(length_cap(5), content_policy(["x"]))
    assert e("hi") is Decision.CONTINUE
    assert e("123456") is Decision.HALT
