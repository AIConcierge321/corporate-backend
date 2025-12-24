import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class RedisService:
    """
    Production-ready Redis service with connection pooling and health checks.
    
    MED-002: Enhanced with:
    - Connection pool configuration
    - Health check method
    - Retry logic for transient failures
    - Connection timeout configuration
    - Proper error handling
    """
    _request_client: redis.Redis | None = None
    _connection_pool: redis.ConnectionPool | None = None

    @classmethod
    def get_client(cls) -> redis.Redis:
        """Get Redis client with connection pooling."""
        if cls._request_client is None:
            try:
                cls._connection_pool = redis.ConnectionPool.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    max_connections=50,              # Maximum connections in pool
                    retry_on_timeout=True,           # Retry on timeout
                    socket_connect_timeout=5,        # 5s connection timeout
                    socket_timeout=5,                # 5s read/write timeout
                    health_check_interval=30,        # Check connection health every 30s
                )
                cls._request_client = redis.Redis(
                    connection_pool=cls._connection_pool
                )
                logger.info("Redis client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Redis client: {e}")
                raise
        return cls._request_client

    @classmethod
    async def health_check(cls) -> bool:
        """
        Check if Redis is available.
        
        Returns:
            True if Redis is healthy, False otherwise
        """
        try:
            client = cls.get_client()
            await client.ping()
            return True
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis health check failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during Redis health check: {e}")
            return False

    @classmethod
    async def close(cls):
        """Close Redis connections and cleanup resources."""
        if cls._request_client:
            try:
                await cls._request_client.close()
                logger.info("Redis client closed")
            except Exception as e:
                logger.error(f"Error closing Redis client: {e}")
            finally:
                cls._request_client = None
        
        if cls._connection_pool:
            try:
                await cls._connection_pool.disconnect()
                logger.info("Redis connection pool disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting Redis pool: {e}")
            finally:
                cls._connection_pool = None


async def get_redis() -> redis.Redis:
    """Dependency that provides a Redis client."""
    return RedisService.get_client()

