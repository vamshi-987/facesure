import redis
import json
from functools import wraps
from config import Config

# Redis connection pool
redis_client = redis.Redis(
    host=Config.REDIS_HOST or 'localhost',
    port=Config.REDIS_PORT or 6379,
    db=0,
    decode_responses=True,
    max_connections=50
)

def cache_result(ttl=300):
    """Cache decorator for expensive database queries"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            # Try to get from cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            # Execute function and cache result
            result = func(*args, **kwargs)
            redis_client.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator

def invalidate_user_cache(user_id):
    """Clear all cached data for a user"""
    pattern = f"*{user_id}*"
    for key in redis_client.scan_iter(match=pattern):
        redis_client.delete(key)
