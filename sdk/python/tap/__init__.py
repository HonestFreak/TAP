"""TAP — Token Access Protocol.

Top-level public exports. Anything not re-exported here is considered an
implementation detail and may move between releases.
"""

from tap.consumer.client import TapConsumer
from tap.consumer.session import ConsumerSession
from tap.evaluators import compose, content_policy, json_schema, length_cap, topic_drift
from tap.evaluators.base import Decision, Evaluator
from tap.producer.server import TapProducer

__all__ = [
    "ConsumerSession",
    "Decision",
    "Evaluator",
    "TapConsumer",
    "TapProducer",
    "compose",
    "content_policy",
    "json_schema",
    "length_cap",
    "topic_drift",
]

__version__ = "0.1.0"
