"""Redis stream for conversation events.

Adapted from Medallion AI Phone Agent (apps/ai_chat/stream/redis_stream.py).
"""

import json
import time
from collections.abc import AsyncGenerator
from typing import Any

import redis.asyncio as aioredis
from django.conf import settings

from stream.events import StreamEvent, StreamEventType

STREAM_TIMEOUT = 30 * 60
MAX_STREAM_LENGTH = 1000
READ_BATCH_SIZE = 8
READ_BLOCK_MS = 50


def get_stream_key(conversation_id: str) -> str:
    return f"conversation-stream:{conversation_id}"


async def get_redis_connection():
    redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6381/0")
    return await aioredis.from_url(redis_url)


class ConversationRedisStream:
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.key = get_stream_key(conversation_id)
        self._redis: Any = None

    async def __aenter__(self) -> "ConversationRedisStream":
        self._redis = await get_redis_connection()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def write_event(self, event: StreamEvent) -> str:
        if not self._redis:
            raise RuntimeError("Must use as async context manager")

        data = json.dumps(
            {
                "event": event.model_dump(),
                "event_type": event.type.value,
                "timestamp": time.time(),
            }
        ).encode()

        msg_id = await self._redis.xadd(
            self.key,
            {"data": data},
            maxlen=MAX_STREAM_LENGTH,
            approximate=True,
        )
        await self._redis.expire(self.key, STREAM_TIMEOUT)
        return msg_id

    async def read_events(
        self,
        last_id: str = "0",
        timeout_seconds: int = 30,
    ) -> AsyncGenerator[tuple[str, StreamEvent], None]:
        if not self._redis:
            raise RuntimeError("Must use as async context manager")

        start_time = time.time()

        while True:
            if time.time() - start_time > timeout_seconds:
                break

            results = await self._redis.xread(
                {self.key: last_id},
                count=READ_BATCH_SIZE,
                block=READ_BLOCK_MS,
            )

            if not results:
                continue

            for _stream_key, messages in results:
                for msg_id, data in messages:
                    last_id = msg_id.decode() if isinstance(msg_id, bytes) else msg_id
                    payload = json.loads(data[b"data"])
                    event = StreamEvent(**payload["event"])
                    yield last_id, event

                    if event.type in (StreamEventType.COMPLETE, StreamEventType.ERROR):
                        return

    async def delete(self) -> None:
        if self._redis:
            await self._redis.delete(self.key)

    async def exists(self) -> bool:
        if self._redis:
            return bool(await self._redis.exists(self.key))
        return False


class StreamWriter:
    """Simplified writer for Temporal activities."""

    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.key = get_stream_key(conversation_id)
        self._redis: Any = None

    async def connect(self) -> None:
        self._redis = await get_redis_connection()

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def write(self, event: StreamEvent) -> str:
        if not self._redis:
            await self.connect()

        data = json.dumps(
            {
                "event": event.model_dump(),
                "event_type": event.type.value,
                "timestamp": time.time(),
            }
        ).encode()

        msg_id = await self._redis.xadd(
            self.key,
            {"data": data},
            maxlen=MAX_STREAM_LENGTH,
            approximate=True,
        )
        await self._redis.expire(self.key, STREAM_TIMEOUT)
        return msg_id
