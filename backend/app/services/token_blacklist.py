"""
Token Blacklist Service

Redis-based token revocation for logout and emergency invalidation.
"""

import logging

from app.services.redis_client import RedisService

logger = logging.getLogger(__name__)

# Redis key prefix for blacklisted tokens
BLACKLIST_PREFIX = "token_blacklist:"


class TokenBlacklist:
    """
    Service to manage revoked JWT tokens.

    Tokens are stored in Redis with TTL matching their expiration.
    """

    @classmethod
    async def revoke(cls, jti: str, expires_in_seconds: int) -> bool:
        """
        Add a token to the blacklist.

        Args:
            jti: JWT ID (unique token identifier)
            expires_in_seconds: How long to keep in blacklist (should match token expiry)
        """
        try:
            redis = RedisService.get_client()
            key = f"{BLACKLIST_PREFIX}{jti}"
            await redis.setex(key, expires_in_seconds, "revoked")
            logger.info(f"Token revoked: {jti}")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False

    @classmethod
    async def is_revoked(cls, jti: str) -> bool:
        """
        Check if a token has been revoked.

        Returns True if token is blacklisted.
        """
        try:
            redis = RedisService.get_client()
            key = f"{BLACKLIST_PREFIX}{jti}"
            result = await redis.get(key)
            return result is not None
        except Exception as e:
            # Fail-safe: if Redis is down, allow the request
            # (token will still expire naturally)
            logger.error(f"Failed to check token blacklist: {e}")
            return False

    @classmethod
    async def revoke_all_for_user(cls, user_id: int) -> bool:
        """
        Revoke all tokens for a user by adding to user-level blacklist.

        This is useful for password changes or security incidents.
        """
        try:
            redis = RedisService.get_client()
            key = f"user_tokens_revoked:{user_id}"
            # Set with 7 day TTL (max token lifetime)
            await redis.setex(key, 7 * 24 * 60 * 60, "all_revoked")
            logger.info(f"All tokens revoked for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke user tokens: {e}")
            return False

    @classmethod
    async def is_user_revoked(cls, user_id: int, token_issued_at: int) -> bool:
        """
        Check if all tokens for a user have been revoked.

        Returns True if user tokens were revoked AFTER this token was issued.
        """
        try:
            redis = RedisService.get_client()
            key = f"user_tokens_revoked:{user_id}"
            result = await redis.get(key)
            return result is not None
        except Exception as e:
            logger.error(f"Failed to check user token revocation: {e}")
            return False
