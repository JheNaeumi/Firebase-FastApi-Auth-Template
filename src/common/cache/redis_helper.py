import hashlib
import json
from typing import Any, List, Optional
from redis.asyncio import Redis, from_url
from common.logger import get_logger
import os
from datetime import datetime
logger = get_logger(__name__)

redis_client: Optional[Redis] = None


async def init_redis(redis_url: str) -> Redis:
    """Initialize Redis client on app startup."""
    global redis_client
    try:
        redis_client = await from_url(redis_url, decode_responses=True, password=os.getenv("REDIS_PASSWORD"))
        await redis_client.ping()
        logger.info("Redis connected successfully")
        return redis_client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        raise


async def close_redis() -> None:
    """Close Redis connection on app shutdown."""
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")


def get_redis() -> Redis:
    """Get Redis client instance for dependency injection."""
    if not redis_client:
        raise RuntimeError("Redis client not initialized")
    return redis_client


async def set_with_expiry(
    key: str, value: Any, ttl: int
) -> bool:
    """Set a key with expiration time (TTL in seconds)."""
    try:
        client = get_redis()
        serialized = json.dumps(value) if not isinstance(value, str) else value
        await client.setex(key, ttl, serialized)
        return True
    except Exception as e:
        logger.error(f"Failed to set key {key}: {str(e)}")
        return False


async def get_value(key: str) -> Optional[Any]:
    """Get value from Redis by key."""
    try:
        client = get_redis()
        value = await client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    except Exception as e:
        logger.error(f"Failed to get key {key}: {str(e)}")
        return None


async def delete_key(key: str) -> bool:
    """Delete a key from Redis."""
    try:
        client = get_redis()
        await client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Failed to delete key {key}: {str(e)}")
        return False


async def delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern."""
    try:
        client = get_redis()
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)
            logger.debug(
                f"Deleted {len(keys)} keys matching pattern {pattern}")
            return len(keys)
        return 0
    except Exception as e:
        logger.error(f"Failed to delete pattern {pattern}: {str(e)}")
        return 0


async def key_exists(key: str) -> bool:
    """Check if a key exists in Redis."""
    try:
        client = get_redis()
        return await client.exists(key) > 0
    except Exception as e:
        logger.error(f"Failed to check key existence {key}: {str(e)}")
        return False


async def increment_counter(key: str, ttl: int = 900) -> int:
    """Increment a counter and set/renew TTL."""
    try:
        client = get_redis()
        count = await client.incr(key)
        await client.expire(key, ttl)
        return count
    except Exception as e:
        logger.error(f"Failed to increment counter {key}: {str(e)}")
        return 0


# ============= Token Blacklist =============

async def blacklist_token(token: str, user_uid: str, ttl: int) -> bool:
    """Blacklist a token (logout/revoke)."""
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        key = f"blacklist:{token_hash}"
        await set_with_expiry(key, {"user_uid": user_uid}, ttl)
        logger.info(f"Token blacklisted for user {user_uid}")
        return True
    except Exception as e:
        logger.error(f"Failed to blacklist token: {str(e)}")
        return False


async def is_token_blacklisted(token: str) -> bool:
    """Check if a token is blacklisted."""
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        key = f"blacklist:{token_hash}"
        return await key_exists(key)
    except Exception as e:
        logger.error(f"Failed to check token blacklist: {str(e)}")
        return False


# ============= Rate Limiting =============

async def check_rate_limit(
    identifier: str, max_attempts: int, window_seconds: int
) -> bool:
    """Check if identifier exceeded rate limit."""
    try:
        key = f"ratelimit:{identifier}"
        count = await increment_counter(key, window_seconds)

        if count > max_attempts:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return False

        return True
    except Exception as e:
        logger.error(f"Rate limit check failed for {identifier}: {str(e)}")
        return True  # Fail open - allow if Redis unavailable


async def get_rate_limit_remaining(
    identifier: str, max_attempts: int
) -> int:
    """Get remaining attempts for identifier."""
    try:
        key = f"ratelimit:{identifier}"
        client = get_redis()
        count = await client.get(key)
        count = int(count) if count else 0
        return max(0, max_attempts - count)
    except Exception as e:
        logger.error(f"Failed to get rate limit remaining: {str(e)}")
        return max_attempts


async def reset_rate_limit(identifier: str) -> bool:
    """Reset rate limit counter for identifier."""
    try:
        key = f"ratelimit:{identifier}"
        await delete_key(key)
        return True
    except Exception as e:
        logger.error(f"Failed to reset rate limit: {str(e)}")
        return False


# ============= Failed Login Tracking =============

async def increment_failed_login(email: str, window_seconds: int = 900) -> int:
    """Increment failed login counter for email."""
    try:
        key = f"failed_login:{email}"
        count = await increment_counter(key, window_seconds)
        if count == 1:
            logger.info(f"Failed login attempt tracked for {email}")
        return count
    except Exception as e:
        logger.error(f"Failed to increment login counter: {str(e)}")
        return 0


async def get_failed_login_count(email: str) -> int:
    """Get failed login count for email."""
    try:
        key = f"failed_login:{email}"
        client = get_redis()
        count = await client.get(key)
        return int(count) if count else 0
    except Exception as e:
        logger.error(f"Failed to get login count: {str(e)}")
        return 0


async def reset_failed_login(email: str) -> bool:
    """Reset failed login counter for email."""
    try:
        key = f"failed_login:{email}"
        await delete_key(key)
        return True
    except Exception as e:
        logger.error(f"Failed to reset login counter: {str(e)}")
        return False


async def is_account_locked(email: str, max_attempts: int = 5) -> bool:
    """Check if account is locked due to failed logins."""
    try:
        count = await get_failed_login_count(email)
        return count >= max_attempts
    except Exception as e:
        logger.error(f"Failed to check account lock: {str(e)}")
        return False


# ============= Token Caching =============

async def cache_token(user_uid: str, token: str, claims: dict, ttl: int = 3600) -> bool:
    """Cache verified token claims."""
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        key = f"token:{user_uid}:{token_hash}"
        await set_with_expiry(key, claims, ttl)
        return True
    except Exception as e:
        logger.error(f"Failed to cache token: {str(e)}")
        return False


async def get_cached_token(user_uid: str, token: str) -> Optional[dict]:
    """Get cached token claims."""
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        key = f"token:{user_uid}:{token_hash}"
        return await get_value(key)
    except Exception as e:
        logger.error(f"Failed to get cached token: {str(e)}")
        return None


async def invalidate_user_tokens(user_uid: str) -> int:
    """Invalidate all cached tokens for a user."""
    try:
        pattern = f"token:{user_uid}:*"
        return await delete_pattern(pattern)
    except Exception as e:
        logger.error(f"Failed to invalidate user tokens: {str(e)}")
        return 0


# ============= User Caching =============

async def cache_user(user_uid: str, user_data: dict, ttl: int = 3600) -> bool:
    """Cache user profile data."""
    try:
        key = f"user:{user_uid}"
        await set_with_expiry(key, user_data, ttl)
        return True
    except Exception as e:
        logger.error(f"Failed to cache user: {str(e)}")
        return False


async def get_cached_user(user_uid: str) -> Optional[dict]:
    """Get cached user profile data."""
    try:
        key = f"user:{user_uid}"
        return await get_value(key)
    except Exception as e:
        logger.error(f"Failed to get cached user: {str(e)}")
        return None


async def cache_user_by_email(email: str, user_uid: str, ttl: int = 3600) -> bool:
    """Cache user UID by email for quick lookup."""
    try:
        key = f"user_email:{email}"
        await set_with_expiry(key, user_uid, ttl)
        return True
    except Exception as e:
        logger.error(f"Failed to cache user by email: {str(e)}")
        return False


async def get_user_uid_by_email(email: str) -> Optional[str]:
    """Get user UID from email cache."""
    try:
        key = f"user_email:{email}"
        return await get_value(key)
    except Exception as e:
        logger.error(f"Failed to get user UID by email: {str(e)}")
        return None


async def invalidate_user_cache(user_uid: str, email: str = None) -> int:
    """Invalidate all cache for a user."""
    try:
        count = 0
        pattern = f"user:{user_uid}:*"
        count += await delete_pattern(pattern)

        user_key = f"user:{user_uid}"
        if await delete_key(user_key):
            count += 1

        if email:
            email_key = f"user_email:{email}"
            if await delete_key(email_key):
                count += 1

        logger.info(f"Invalidated {count} cache entries for user {user_uid}")
        return count
    except Exception as e:
        logger.error(f"Failed to invalidate user cache: {str(e)}")
        return 0


# ============= Online User Tracking =============

async def set_user_online(user_uid: str, ttl: int = 3600) -> bool:
    """Mark user as online."""
    try:
        key = f"online:{user_uid}"
        await set_with_expiry(key, {"status": "online"}, ttl)
        logger.debug(f"User {user_uid} marked online")
        return True
    except Exception as e:
        logger.error(f"Failed to set user online: {str(e)}")
        return False


async def is_user_online(user_uid: str) -> bool:
    """Check if user is online."""
    try:
        key = f"online:{user_uid}"
        return await key_exists(key)
    except Exception as e:
        logger.error(f"Failed to check user online status: {str(e)}")
        return False


async def get_online_users() -> List[str]:
    """Get list of all online user UIDs."""
    try:
        client = get_redis()
        keys = await client.keys("online:*")
        user_uids = [key.replace("online:", "") for key in keys]
        logger.debug(f"Retrieved {len(user_uids)} online users")
        return user_uids
    except Exception as e:
        logger.error(f"Failed to get online users: {str(e)}")
        return []


async def set_user_offline(user_uid: str) -> bool:
    """Mark user as offline."""
    try:
        key = f"online:{user_uid}"
        await delete_key(key)
        logger.debug(f"User {user_uid} marked offline")
        return True
    except Exception as e:
        logger.error(f"Failed to set user offline: {str(e)}")
        return False


# ============= Session Management (Inactivity Timeout) =============

async def set_session(
    user_uid: str,
    inactivity_ttl: int = 900,
    absolute_ttl: int = None
) -> bool:
    """
    Create user session with inactivity timeout.
    inactivity_ttl: Logout after N seconds of no activity (default 15 min)
    absolute_ttl: Max session duration regardless of activity (optional)
    """
    try:
        # Inactivity session - resets on each request
        inactivity_key = f"session:inactivity:{user_uid}"
        await set_with_expiry(inactivity_key, {"status": "active"}, inactivity_ttl)

        # Absolute session - only set once per login
        if absolute_ttl:
            absolute_key = f"session:absolute:{user_uid}"
            if not await key_exists(absolute_key):
                await set_with_expiry(
                    absolute_key,
                    {"created_at": datetime.now().isoformat()},
                    absolute_ttl
                )

        logger.debug(f"Session created for user {user_uid}")
        return True
    except Exception as e:
        logger.error(f"Failed to set session: {str(e)}")
        return False


async def refresh_session(user_uid: str, inactivity_ttl: int = 900) -> bool:
    """Refresh inactivity timeout on user activity (called on each request)."""
    try:
        key = f"session:inactivity:{user_uid}"
        await set_with_expiry(key, {"status": "active"}, inactivity_ttl)
        return True
    except Exception as e:
        logger.error(f"Failed to refresh session: {str(e)}")
        return False


async def is_session_active(user_uid: str) -> tuple[bool, str]:
    """
    Check if session is active.
    Returns: (is_active, reason)
    """
    try:
        inactivity_key = f"session:inactivity:{user_uid}"
        absolute_key = f"session:absolute:{user_uid}"

        # Check inactivity timeout
        inactivity_active = await key_exists(inactivity_key)
        if not inactivity_active:
            return False, "inactivity_timeout"

        # Check absolute timeout
        absolute_active = await key_exists(absolute_key)
        if not absolute_active:
            return False, "absolute_timeout"

        return True, "active"
    except Exception as e:
        logger.error(f"Failed to check session: {str(e)}")
        return True, "error"  # Fail open


async def get_session_remaining(user_uid: str) -> dict:
    """Get remaining session time."""
    try:
        client = get_redis()
        inactivity_key = f"session:inactivity:{user_uid}"
        absolute_key = f"session:absolute:{user_uid}"

        inactivity_ttl = await client.ttl(inactivity_key)
        absolute_ttl = await client.ttl(absolute_key)

        return {
            "inactivity_remaining_seconds": max(0, inactivity_ttl),
            "absolute_remaining_seconds": max(0, absolute_ttl) if absolute_ttl > 0 else None
        }
    except Exception as e:
        logger.error(f"Failed to get session remaining: {str(e)}")
        return {}


async def clear_session(user_uid: str) -> bool:
    """Clear session on logout."""
    try:
        await delete_key(f"session:inactivity:{user_uid}")
        await delete_key(f"session:absolute:{user_uid}")
        logger.debug(f"Session cleared for user {user_uid}")
        return True
    except Exception as e:
        logger.error(f"Failed to clear session: {str(e)}")
        return False


# ============= Message Queue (Chat Ready) =============

async def publish_message(channel: str, message: dict) -> bool:
    """Publish message to Redis channel (for future chat)."""
    try:
        client = get_redis()
        message_json = json.dumps(message)
        await client.publish(channel, message_json)
        logger.debug(f"Message published to channel {channel}")
        return True
    except Exception as e:
        logger.error(f"Failed to publish message: {str(e)}")
        return False


async def subscribe_to_channel(channel: str):
    """Subscribe to Redis channel (for future chat)."""
    try:
        client = get_redis()
        pubsub = client.pubsub()
        await pubsub.subscribe(channel)
        logger.debug(f"Subscribed to channel {channel}")
        return pubsub
    except Exception as e:
        logger.error(f"Failed to subscribe to channel: {str(e)}")
        return None
