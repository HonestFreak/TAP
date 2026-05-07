"""Anchor instruction discriminators.

Anchor identifies an instruction by `sha256("global:<name>")[:8]`. We
hard-code the eight-byte prefixes here so the SDK doesn't take a dependency
on a SHA implementation at import time."""

from __future__ import annotations

import hashlib


def _disc(name: str) -> bytes:
    return hashlib.sha256(f"global:{name}".encode("utf-8")).digest()[:8]


OPEN_CHANNEL = _disc("open_channel")
SETTLE = _disc("settle")
DISPUTE = _disc("dispute")
CLOSE = _disc("close")
