import hashlib
import json
import logging
from typing import Optional, Dict, Any, Tuple
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisService:
    """
    Enterprise Redis Service managing semantic/exact query hash caching,
    distributed rate limiting, and session state.
    """
    _redis: Optional[aioredis.Redis] = None

    @classmethod
    def get_client(cls) -> Optional[aioredis.Redis]:
        """
        Returns singleton async Redis client instance.
        """
        if not settings.REDIS_URL:
            return None

        if cls._redis is None:
            try:
                cls._redis = aioredis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_timeout=3.0,
                    socket_connect_timeout=3.0
                )
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                return None
        return cls._redis

    @classmethod
    def _compute_query_key(cls, agent_id: str, user_role: str, user_id: str, query: str) -> str:
        raw = f"{agent_id}:{user_role}:{user_id}:{query.strip().lower()}"
        h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"pnp:cache:query:{agent_id}:{h}"

    @classmethod
    async def get_query_cache(
        cls, agent_id: str, user_role: str, user_id: str, query: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves cached query response. Returns None on cache miss or Redis failure.
        """
        client = cls.get_client()
        if not client:
            return None

        try:
            key = cls._compute_query_key(agent_id, user_role, user_id, query)
            val = await client.get(key)
            if val:
                data = json.loads(val)
                data["cached"] = True
                return data
        except Exception as e:
            logger.debug(f"Redis cache lookup failed: {e}")
        return None

    @classmethod
    async def set_query_cache(
        cls, agent_id: str, user_role: str, user_id: str, query: str, response_data: Dict[str, Any], ttl: int = 300
    ) -> bool:
        """
        Stores query response in cache with specified TTL in seconds (default 5 mins).
        """
        client = cls.get_client()
        if not client:
            return False

        try:
            key = cls._compute_query_key(agent_id, user_role, user_id, query)
            # Exclude transient or error payloads
            if "error" in response_data or not response_data.get("answer"):
                return False
            payload = json.dumps(response_data)
            await client.set(key, payload, ex=ttl)
            return True
        except Exception as e:
            logger.debug(f"Redis cache write failed: {e}")
            return False

    @classmethod
    async def check_rate_limit(
        cls, identifier: str, limit: int = 60, window_seconds: int = 60
    ) -> Tuple[bool, int, int]:
        """
        Sliding-window distributed rate limiter.
        Returns: (is_allowed: bool, current_usage: int, retry_after_seconds: int)
        """
        client = cls.get_client()
        if not client:
            # If Redis unavailable, fail open to avoid service outage
            return True, 0, 0

        try:
            key = f"pnp:ratelimit:{identifier}"
            pipeline = client.pipeline()
            pipeline.incr(key)
            pipeline.ttl(key)
            results = await pipeline.execute()

            current_count = results[0]
            ttl = results[1]

            if ttl == -1:
                # Key was just created with no TTL
                await client.expire(key, window_seconds)
                ttl = window_seconds

            if current_count > limit:
                return False, current_count, max(1, ttl)
            return True, current_count, 0
        except Exception as e:
            logger.debug(f"Redis rate limit check failed: {e}")
            return True, 0, 0
