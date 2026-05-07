"""Type aliases for handler functions registered with `TapProducer`. Pulled
into a separate module so circular-import warnings between `server.py` and
`wrap_stream.py` don't appear when the producer is built up incrementally."""

from __future__ import annotations

from typing import Any, AsyncIterator, Callable, Coroutine

ModelStream = AsyncIterator[str]
"""Raw token-by-token output from the wrapped model SDK."""

HandlerFn = Callable[[dict[str, Any]], Coroutine[Any, Any, ModelStream]]
"""Producer-side request handler.

Receives the parsed request body, returns an async iterator over the
model's tokens. The TAP framework wraps the iterator with payment metering
before forwarding to the consumer."""
