import redis.asyncio as redis
from app.core.config import settings
import asyncio
import logging

import redis.asyncio as redis
from app.core.config import settings
import asyncio
import logging

redis_client = None

async def get_redis():
    global redis_client
    if not redis_client:
        redis_client = redis.from_url(settings.REDIS_URL, socket_timeout=0.1, socket_connect_timeout=0.1)
    return redis_client

async def cache_get(key):
    try:
        r = await get_redis()
        val = await asyncio.wait_for(r.get(key), timeout=0.1)
        return val
    except Exception as e:
        logging.warning(f"Redis cache_get timeout or error: {e}")
        return None

async def cache_set(key, value, expire=60):
    try:
        r = await get_redis()
        await asyncio.wait_for(r.set(key, value, ex=expire), timeout=0.1)
    except Exception as e:
        logging.warning(f"Redis cache_set timeout or error: {e}")
