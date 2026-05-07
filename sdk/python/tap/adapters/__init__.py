"""Model SDK adapters. Each adapter exposes a single async function returning
an `AsyncIterator[str]` of token deltas, decoupling the producer wrapper
from any one provider's streaming format.

Imports inside each adapter are lazy so the base SDK does not require the
provider packages to be installed."""

from tap.adapters.anthropic import stream_anthropic
from tap.adapters.gemini import stream_gemini
from tap.adapters.ollama import stream_ollama
from tap.adapters.openai import stream_openai

__all__ = ["stream_anthropic", "stream_gemini", "stream_ollama", "stream_openai"]
