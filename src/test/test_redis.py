"""
Test suite for Redis integration in FastAPI auth boilerplate.
Run with: pytest src/test/test_redis.py -v
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from common.cache import redis_helper
from common.logger import get_logger

logger = get_logger(__name__)


@pytest.fixture(scope="session")
async def redis_conn():
    """Initialize Redis for testing."""
    await redis_helper.init_redis("redis://localhost:6379/0")
    yield
    await redis_helper.close_redis()


@pytest.mark.asyncio
async def test_redis_connection(redis_conn):
    """Test basic Redis connection."""
    client = redis_helper.get_redis()
    assert client is not None
    logger.info("✓ Redis connection successful")


@pytest.mark.asyncio
async def test_set_and_get_value(redis_conn):
    """Test basic set/get operations."""
    key = "test:basic"
    value = {"user": "john", "email": "john@example.com"}

    # Set value
    result = await redis_helper.set_with_expiry(key, value, 3600)
    assert result is True

    # Get value
    retrieved = await redis_helper.get_value(key)
    assert retrieved == value

    # Cleanup
    await redis_helper.delete_key(key)
    logger.info("✓ Set/Get operations work")


@pytest.mark.asyncio
async def test_rate_limiting(redis_conn):
    """Test rate limiting functionality."""
    email = "ratelimit@test.com"
    max_attempts = 5
    window = 900

    # Should allow first 5 attempts
    for i in range(1, max_attempts + 1):
        allowed = await redis_helper.check_rate_limit(email, max_attempts, window)
        assert allowed is True, f"Attempt {i} should be allowed"

    # 6th attempt should be blocked
    allowed = await redis_helper.check_rate_limit(email, max_attempts, window)
    assert allowed is False, "6th attempt should be blocked"

    # Remaining should be 0
    remaining = await redis_helper.get_rate_limit_remaining(email, max_attempts)
    assert remaining == 0

    # Cleanup
    await redis_helper.reset_rate_limit(email)
    logger.info("✓ Rate limiting works correctly")


@pytest.mark.asyncio
async def test_failed_login_tracking(redis_conn):
    """Test failed login attempt tracking."""
    email = "failedlogin@test.com"
    max_attempts = 5
    window = 900

    # Simulate 5 failed login attempts
    for i in range(1, max_attempts + 1):
        count = await redis_helper.increment_failed_login(email, window)
        assert count == i, f"Failed login count should be {i}"

    # Check if account is locked
    locked = await redis_helper.is_account_locked(email, max_attempts)
    assert locked is True, "Account should be locked after 5 failed attempts"

    # Reset and verify
    await redis_helper.reset_failed_login(email)
    count = await redis_helper.get_failed_login_count(email)
    assert count == 0, "Failed login count should be reset to 0"

    locked = await redis_helper.is_account_locked(email, max_attempts)
    assert locked is False, "Account should be unlocked"

    logger.info("✓ Failed login tracking works correctly")


@pytest.mark.asyncio
async def test_token_blacklist(redis_conn):
    """Test token blacklisting."""
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token"
    user_uid = "user123"
    ttl = 3600

    # Token should not be blacklisted initially
    blacklisted = await redis_helper.is_token_blacklisted(token)
    assert blacklisted is False

    # Blacklist the token
    result = await redis_helper.blacklist_token(token, user_uid, ttl)
    assert result is True

    # Now token should be blacklisted
    blacklisted = await redis_helper.is_token_blacklisted(token)
    assert blacklisted is True

    # Cleanup
    token_hash = __import__('hashlib').sha256(token.encode()).hexdigest()[:16]
    await redis_helper.delete_key(f"blacklist:{token_hash}")
    logger.info("✓ Token blacklist works correctly")


@pytest.mark.asyncio
async def test_token_caching(redis_conn):
    """Test token claims caching."""
    user_uid = "user456"
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token2"
    claims = {
        "uid": user_uid,
        "email": "test@example.com",
        "email_verified": True,
        "exp": int((datetime.now() + timedelta(hours=1)).timestamp())
    }

    # Cache should be empty initially
    cached = await redis_helper.get_cached_token(user_uid, token)
    assert cached is None

    # Cache the token claims
    result = await redis_helper.cache_token(user_uid, token, claims)
    assert result is True

    # Retrieve from cache
    cached = await redis_helper.get_cached_token(user_uid, token)
    assert cached == claims

    # Invalidate user tokens
    count = await redis_helper.invalidate_user_tokens(user_uid)
    assert count >= 1

    logger.info("✓ Token caching works correctly")


@pytest.mark.asyncio
async def test_online_user_tracking(redis_conn):
    """Test online user status tracking."""
    user_uid1 = "user_online_1"
    user_uid2 = "user_online_2"
    ttl = 3600

    # Initially no online users
    online_users = await redis_helper.get_online_users()
    initial_count = len(online_users)

    # Set users online
    await redis_helper.set_user_online(user_uid1, ttl)
    await redis_helper.set_user_online(user_uid2, ttl)

    # Check individual status
    is_online1 = await redis_helper.is_user_online(user_uid1)
    is_online2 = await redis_helper.is_user_online(user_uid2)
    assert is_online1 is True
    assert is_online2 is True

    # Get all online users
    online_users = await redis_helper.get_online_users()
    assert user_uid1 in online_users
    assert user_uid2 in online_users
    assert len(online_users) == initial_count + 2

    # Set user offline
    await redis_helper.set_user_offline(user_uid1)
    is_online1 = await redis_helper.is_user_online(user_uid1)
    assert is_online1 is False

    # Cleanup
    await redis_helper.set_user_offline(user_uid2)
    logger.info("✓ Online user tracking works correctly")


@pytest.mark.asyncio
async def test_user_caching(redis_conn):
    """Test user profile caching."""
    user_uid = "user789"
    email = "cache@example.com"
    user_data = {
        "uid": user_uid,
        "email": email,
        "first_name": "John",
        "last_name": "Doe",
        "profile_image": "profile_uuid"
    }

    # Cache user data
    result = await redis_helper.cache_user(user_uid, user_data)
    assert result is True

    # Retrieve cached user
    cached = await redis_helper.get_cached_user(user_uid)
    assert cached == user_data

    # Cache user by email
    result = await redis_helper.cache_user_by_email(email, user_uid)
    assert result is True

    # Retrieve user UID by email
    cached_uid = await redis_helper.get_user_uid_by_email(email)
    assert cached_uid == user_uid

    # Invalidate user cache
    count = await redis_helper.invalidate_user_cache(user_uid, email)
    assert count >= 2

    # Verify invalidation
    cached = await redis_helper.get_cached_user(user_uid)
    assert cached is None

    logger.info("✓ User caching works correctly")


@pytest.mark.asyncio
async def test_key_expiration(redis_conn):
    """Test that keys expire correctly."""
    key = "test:expiring_key"
    value = "test_value"
    ttl = 2  # 2 seconds

    # Set key with short TTL
    await redis_helper.set_with_expiry(key, value, ttl)

    # Should exist immediately
    exists = await redis_helper.key_exists(key)
    assert exists is True

    # Wait for expiration
    await asyncio.sleep(3)

    # Should not exist after expiration
    exists = await redis_helper.key_exists(key)
    assert exists is False

    logger.info("✓ Key expiration works correctly")


@pytest.mark.asyncio
async def test_pattern_deletion(redis_conn):
    """Test deleting multiple keys by pattern."""
    # Create multiple related keys
    await redis_helper.set_with_expiry("test:pattern:1", "value1", 3600)
    await redis_helper.set_with_expiry("test:pattern:2", "value2", 3600)
    await redis_helper.set_with_expiry("test:pattern:3", "value3", 3600)
    await redis_helper.set_with_expiry("other:key", "value4", 3600)

    # Delete by pattern
    count = await redis_helper.delete_pattern("test:pattern:*")
    assert count == 3

    # Verify pattern keys are deleted
    exists1 = await redis_helper.key_exists("test:pattern:1")
    exists2 = await redis_helper.key_exists("test:pattern:2")
    exists_other = await redis_helper.key_exists("other:key")

    assert exists1 is False
    assert exists2 is False
    assert exists_other is True

    # Cleanup
    await redis_helper.delete_key("other:key")
    logger.info("✓ Pattern deletion works correctly")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
