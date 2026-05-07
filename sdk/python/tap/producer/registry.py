"""In-memory registry of active channels keyed by channel ID.

A more elaborate producer might persist this to Redis or Postgres. The
abstraction is small enough (`get`, `put`, `remove`) that swapping the
implementation requires touching only this file."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from solders.pubkey import Pubkey

from tap.producer.channel import ActiveChannel


class ChannelRegistry:
    def __init__(self) -> None:
        self._channels: dict[Pubkey, ActiveChannel] = {}
        self._lock = asyncio.Lock()

    async def put(self, channel: ActiveChannel) -> None:
        async with self._lock:
            self._channels[channel.channel_id] = channel

    async def get(self, channel_id: Pubkey) -> ActiveChannel | None:
        async with self._lock:
            return self._channels.get(channel_id)

    async def remove(self, channel_id: Pubkey) -> ActiveChannel | None:
        async with self._lock:
            return self._channels.pop(channel_id, None)

    async def snapshot(self) -> Iterable[ActiveChannel]:
        async with self._lock:
            return list(self._channels.values())
