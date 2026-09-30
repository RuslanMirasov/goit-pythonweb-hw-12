"""Підключення до Redis, що використовується як кеш."""

import redis.asyncio as redis

from src.conf.config import settings

redis_client = redis.Redis(
    host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True
)


async def get_redis():
    """
    Залежність FastAPI, що надає клієнт Redis.

    Returns:
        Асинхронний клієнт Redis.
    """
    return redis_client
