---
title: Tokenizer registry
sidebar_position: 6
---

# Tokenizer registry

`tap.tokenizer` is a process-local registry mapping `tokenizer_id`
strings to deterministic `Callable[[str], int]` functions. Both
producer and consumer use the same registry, but for different roles:

- **Producer**: counts input tokens at 402 time to compute
  `input_token_count` / `prepaid_input_micro`.
- **Consumer**: re-tokenizes the same prompt locally with the same
  identifier to verify the producer's count (whitepaper §5.3.7).

## Default tokenizer

The SDK ships with `tap.tok.v1` registered: a deterministic,
dependency-free whitespace-and-punctuation split. Useful for demos.

```python
from tap import tokenizer

assert tokenizer.is_registered("tap.tok.v1")
assert tokenizer.count("tap.tok.v1", "Hello, world!") == 4
```

## Registering production tokenizers

Plug in `tiktoken` for OpenAI / Anthropic models:

```python
import tiktoken
from tap import tokenizer

enc = tiktoken.get_encoding("cl100k_base")
tokenizer.register("cl100k_base", lambda text: len(enc.encode(text)))
```

Or the model vendor's own SDK:

```python
from google import genai
client = genai.Client()

def gemini_count(text: str) -> int:
    return client.models.count_tokens(model="gemini-2.5-flash", contents=text).total_tokens

tokenizer.register("gemini-2.5-flash", gemini_count)
```

Then publish the same `tokenizer_id` in your producer's `Pricing`,
and ensure consumers register the same identifier locally.

## Why deterministic

The §5.3.7 input-inflation defense relies on **bit-for-bit identical**
counts between producer and consumer. Tokenizers like `cl100k_base`
satisfy this trivially. If you write a custom tokenizer, make sure:

- It depends only on the input text (no time-of-day, no environment).
- It's stable across Python versions and platforms (no hash-randomized
  iteration order, no `set` ordering dependencies).
- Its result is `int` exactly — not float, not approximate.

The registry will surface mismatches as `X402Error("does not match
local count")` at session open, before any funds escrow.
