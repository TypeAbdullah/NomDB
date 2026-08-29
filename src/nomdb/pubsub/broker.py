"""
Pub/Sub Broker Engine.
Handles channel subscriptions, glob pattern matching, and message broadcasting.
"""

from __future__ import annotations
import fnmatch
from typing import TYPE_CHECKING, Dict, List, Set, Tuple
from nomdb.protocol.encoder import RESPEncoder

if TYPE_CHECKING:
    from nomdb.server.connection import ClientConnection


class PubSubBroker:
    """Broker maintaining channel and pattern subscriptions across active client connections."""

    def __init__(self):
        # channel_name (bytes) -> set of ClientConnection
        self._channel_subscribers: Dict[bytes, Set[ClientConnection]] = {}
        # pattern (bytes) -> set of ClientConnection
        self._pattern_subscribers: Dict[bytes, Set[ClientConnection]] = {}

    def subscribe(self, client: ClientConnection, channels: List[bytes]) -> List[Tuple[bytes, int]]:
        """Subscribe client to channel(s). Returns list of (channel, current_sub_count)."""
        results = []
        for ch in channels:
            if ch not in self._channel_subscribers:
                self._channel_subscribers[ch] = set()
            self._channel_subscribers[ch].add(client)
            client.subscribed_channels.add(ch)
            results.append((ch, client.total_subscriptions))
        return results

    def unsubscribe(self, client: ClientConnection, channels: List[bytes]) -> List[Tuple[bytes, int]]:
        """Unsubscribe client from channel(s). If channels empty, unsubscribe from all channels."""
        target_channels = channels if channels else list(client.subscribed_channels)
        results = []
        for ch in target_channels:
            if ch in self._channel_subscribers:
                self._channel_subscribers[ch].discard(client)
                if not self._channel_subscribers[ch]:
                    del self._channel_subscribers[ch]
            client.subscribed_channels.discard(ch)
            results.append((ch, client.total_subscriptions))
        return results

    def psubscribe(self, client: ClientConnection, patterns: List[bytes]) -> List[Tuple[bytes, int]]:
        """Subscribe client to pattern(s). Returns list of (pattern, current_sub_count)."""
        results = []
        for pat in patterns:
            if pat not in self._pattern_subscribers:
                self._pattern_subscribers[pat] = set()
            self._pattern_subscribers[pat].add(client)
            client.subscribed_patterns.add(pat)
            results.append((pat, client.total_subscriptions))
        return results

    def punsubscribe(self, client: ClientConnection, patterns: List[bytes]) -> List[Tuple[bytes, int]]:
        """Unsubscribe client from pattern(s). If empty, unsubscribe from all patterns."""
        target_patterns = patterns if patterns else list(client.subscribed_patterns)
        results = []
        for pat in target_patterns:
            if pat in self._pattern_subscribers:
                self._pattern_subscribers[pat].discard(client)
                if not self._pattern_subscribers[pat]:
                    del self._pattern_subscribers[pat]
            client.subscribed_patterns.discard(pat)
            results.append((pat, client.total_subscriptions))
        return results

    def publish(self, channel: bytes, message: bytes) -> int:
        """
        Publish message to channel and matching patterns.
        Returns count of subscribers that received message.
        """
        receivers = 0
        channel_str = channel.decode("utf-8", errors="replace")

        # 1. Direct channel subscribers
        if channel in self._channel_subscribers:
            msg_payload = RESPEncoder.encode([b"message", channel, message])
            for client in list(self._channel_subscribers[channel]):
                client.send_raw(msg_payload)
                receivers += 1

        # 2. Pattern subscribers
        for pattern, subscribers in list(self._pattern_subscribers.items()):
            pat_str = pattern.decode("utf-8", errors="replace")
            if fnmatch.fnmatch(channel_str, pat_str):
                msg_payload = RESPEncoder.encode([b"pmessage", pattern, channel, message])
                for client in list(subscribers):
                    client.send_raw(msg_payload)
                    receivers += 1

        return receivers

    def remove_connection(self, client: ClientConnection) -> None:
        """Clean up all channel/pattern subscriptions when connection drops."""
        for ch in list(client.subscribed_channels):
            if ch in self._channel_subscribers:
                self._channel_subscribers[ch].discard(client)
                if not self._channel_subscribers[ch]:
                    del self._channel_subscribers[ch]
        client.subscribed_channels.clear()

        for pat in list(client.subscribed_patterns):
            if pat in self._pattern_subscribers:
                self._pattern_subscribers[pat].discard(client)
                if not self._pattern_subscribers[pat]:
                    del self._pattern_subscribers[pat]
        client.subscribed_patterns.clear()
