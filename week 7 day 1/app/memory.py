import json
from redis.asyncio import Redis
from app.config import get_settings

class SessionMemory:
    def __init__(self):
        self.settings=get_settings()
        self.redis=Redis.from_url(self.settings.redis_url, decode_responses=True)

    def _messages_key(self, session_id: str) -> str: return f"travel:session:{session_id}:messages"
    def _trip_key(self, session_id: str) -> str: return f"travel:session:{session_id}:trip_id"

    async def ping(self): return await self.redis.ping()

    async def get_messages(self, session_id: str) -> list[dict]:
        values=await self.redis.lrange(self._messages_key(session_id), 0, -1)
        return [json.loads(v) for v in values]

    async def add_message(self, session_id: str, role: str, content: str) -> None:
        key=self._messages_key(session_id)
        await self.redis.rpush(key, json.dumps({"role":role,"content":content}))
        await self.redis.ltrim(key, -self.settings.memory_max_messages, -1)
        await self.redis.expire(key, self.settings.memory_ttl_seconds)

    async def set_trip_id(self, session_id: str, trip_id: int) -> None:
        await self.redis.set(self._trip_key(session_id), trip_id, ex=self.settings.memory_ttl_seconds)

    async def get_trip_id(self, session_id: str) -> int | None:
        value=await self.redis.get(self._trip_key(session_id))
        return int(value) if value else None

    async def close(self): await self.redis.aclose()
