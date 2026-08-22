
# * FIXED WINDOW ALGO

import redis 
from app.config import settings

redis_client = redis.from_url(settings.redis_url, decode_responses=True)

RATE_LIMIT = 10
WINDOW_SECONDS = 60

def check_rate_limit(client_id: str) -> bool:
    key = f"rate_limit:{client_id}"

    current = redis_client.incr(key)
    # * Redis INCR command atomically increments a counter stored at key by 1 ATOMIC in sense if 
    # * 100 req hit at exact same moment Redis guarantees ech increment happens at one at a time with no race condidtion 
    # * you will never get wrog count from concurrent requests

    if current == 1:
        redis_client.expire(key, WINDOW_SECONDS)
    # * first time the client make the request, we set the key to expire after 60 seconds

    answer = current <= RATE_LIMIT
    return answer
    # * if till 10 req the true else false created RateLimitExceededError