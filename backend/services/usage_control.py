import uuid
from dataclasses import dataclass
from datetime import date

import redis.asyncio as aioredis
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from repository.usage_repo import UsageRepository
from settings.config import settings


RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return current
"""

RELEASE_LOCK_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
"""


@dataclass
class GenerationPermit:
    redis: aioredis.Redis
    lock_key: str
    lock_value: str

    async def release(self) -> None:
        try:
            await self.redis.eval(
                RELEASE_LOCK_SCRIPT, 1, self.lock_key, self.lock_value
            )
        except Exception:
            # The lock has a short TTL, so a Redis outage cannot leave it permanent.
            pass


async def _check_window(
        redis: aioredis.Redis, key: str, limit: int, seconds: int
) -> None:
    try:
        current = await redis.eval(RATE_LIMIT_SCRIPT, 1, key, seconds)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="请求保护服务暂时不可用，请稍后重试",
        ) from exc
    if int(current) > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试",
            headers={"Retry-After": str(seconds)},
        )


async def acquire_generation_permit(
        redis: aioredis.Redis,
        session: AsyncSession,
        user_id: int,
        role: str,
        client_ip: str) -> GenerationPermit:
    await _check_window(redis, f"rate:name:user:{user_id}", settings.NAME_USER_RATE_LIMIT, 60)
    await _check_window(redis, f"rate:name:ip:{client_ip}", settings.NAME_IP_RATE_LIMIT, 60)
    await _check_window(redis, "rate:name:global", settings.NAME_GLOBAL_RATE_LIMIT, 60)

    lock_key = f"lock:name:user:{user_id}"
    lock_value = uuid.uuid4().hex
    try:
        acquired = await redis.set(
            lock_key, lock_value, nx=True, ex=settings.NAME_GENERATION_LOCK_SECONDS
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="请求保护服务暂时不可用，请稍后重试",
        ) from exc
    if not acquired:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="已有一个起名请求正在处理中，请勿重复提交",
        )

    permit = GenerationPermit(redis, lock_key, lock_value)
    try:
        if role != "admin":
            used = await UsageRepository(session).daily_used(user_id, date.today())
            if used >= settings.DAILY_FREE_GENERATIONS:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"今日免费生成次数已用完（每日 {settings.DAILY_FREE_GENERATIONS} 次）",
                )
        return permit
    except Exception:
        await permit.release()
        raise
