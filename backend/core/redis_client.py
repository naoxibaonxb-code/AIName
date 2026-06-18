# core/redis_client.py
from typing import AsyncGenerator

from settings.config import settings
import redis.asyncio as aioredis

REDIS_URL = settings.redis_url

redis_client = aioredis.from_url(
    REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
)

async def get_redis_client() ->  AsyncGenerator[aioredis.Redis, None]:
    yield redis_client