"""Consumer-side TAP. The package boundary is `TapConsumer`; everything
else is wiring."""

from tap.consumer.client import TapConsumer
from tap.consumer.session import ConsumerSession, TokenChunk

__all__ = ["ConsumerSession", "TapConsumer", "TokenChunk"]
