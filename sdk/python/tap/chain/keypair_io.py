"""Load a Solana keypair from either a filesystem path or an inline JSON array.

Hosted environments (Render, Fly, ECS) typically inject secrets as env vars
rather than files. Supporting both shapes from the same accessor lets demo
scripts and the producer service stay agnostic to which deployment style is
in use, instead of branching at every call site."""

from __future__ import annotations

import json
from pathlib import Path

from solders.keypair import Keypair


def load_keypair(path_or_json: str) -> Keypair:
    """Return a `Keypair` from either:

    * an inline JSON byte array (`[123, 45, ...]`) — typical when the keypair
      is supplied via an env var, or
    * a filesystem path to such a JSON file (with `~` expanded).
    """
    text = path_or_json.strip()
    if text.startswith("["):
        raw = json.loads(text)
    else:
        raw = json.loads(Path(text).expanduser().read_text())
    return Keypair.from_bytes(bytes(raw))
