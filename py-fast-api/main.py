
import asyncio
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from redis_fastapi import FastAPIRedis, rate_limit


# In-memory state for the demonstration algorithms.
# In production, use a shared backend for multiple workers.
sliding_requests = defaultdict(deque)
token_buckets = {}
bucket_locks = defaultdict(asyncio.Lock)

concurrency_limit = asyncio.Semaphore(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Rate Limiting Demo",
    lifespan=lifespan,
)

# Configure Redis-backed rate limiting.
FastAPIRedis(app).lifespan().rate_limiting()


def client_key(request: Request) -> str:
    """Use the client IP as the rate-limit key."""
    return request.client.host if request.client else "unknown"


# 1. Fixed Window: 3 requests per 10 seconds.
@app.get(
    "/fixed",
    dependencies=[Depends(rate_limit("3/10seconds"))],
)
async def fixed_window():
    return {
        "endpoint": "fixed",
        "limit": "3 requests per 10 seconds",
    }


# 2. Sliding Window: 15 requests per 5 seconds.
# Each client has its own timestamp queue.
async def sliding_window_check(request: Request):
    key = client_key(request)
    now = time.monotonic()
    window = 5.0
    limit = 15

    requests = sliding_requests[key]

    while requests and requests[0] <= now - window:
        requests.popleft()

    if len(requests) >= limit:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Try again later.",
        )

    requests.append(now)


@app.get(
    "/sliding",
    dependencies=[Depends(sliding_window_check)],
)
async def sliding_window():
    return {
        "endpoint": "sliding",
        "limit": "15 requests per 5 seconds",
    }


# 3. Token Bucket: capacity 100, replenish 10 tokens
# every 5 seconds.
async def token_bucket_check(request: Request):
    key = client_key(request)

    capacity = 100
    refill_rate = 10 / 5  # 2 tokens per second
    now = time.monotonic()

    async with bucket_locks[key]:
        tokens, last_update = token_buckets.get(
            key, (float(capacity), now)
        )

        tokens = min(
            capacity,
            tokens + (now - last_update) * refill_rate,
        )

        if tokens < 1:
            raise HTTPException(
                status_code=429,
                detail="Token bucket exhausted. Try again later.",
            )

        token_buckets[key] = (tokens - 1, now)


@app.get(
    "/token",
    dependencies=[Depends(token_bucket_check)],
)
async def token_bucket():
    return {
        "endpoint": "token",
        "capacity": 100,
        "replenishment": "10 tokens every 5 seconds",
    }


# 4. Concurrency: at most 5 requests executing at once.
# Excess requests are rejected immediately.
async def concurrency_check():
    if concurrency_limit.locked():
        raise HTTPException(
            status_code=429,
            detail="Maximum concurrent requests reached.",
        )

    # This check-and-acquire sequence is not atomic.
    # Use the safer implementation below instead.


@app.get("/concurrency")
async def concurrency():
    # Atomically acquire a permit without waiting.
    # asyncio.Semaphore has no acquire_nowait(), so use a
    # lock to make the permit check and acquisition atomic.
    async with concurrency_guard:
        if concurrency_limit.locked():
            raise HTTPException(
                status_code=429,
                detail="Maximum concurrent requests reached.",
            )
        await concurrency_limit.acquire()

    try:
        await asyncio.sleep(2)  # Simulate expensive work.
        return {
            "endpoint": "concurrency",
            "maximum_concurrent_requests": 5,
        }
    finally:
        concurrency_limit.release()


concurrency_guard = asyncio.Lock()


# 5. Custom Sliding Window: 100 requests per minute.
async def custom_sliding_check(request: Request):
    key = client_key(request)
    now = time.monotonic()
    window = 60.0
    limit = 100

    requests = sliding_requests[("custom", key)]

    while requests and requests[0] <= now - window:
        requests.popleft()

    if len(requests) >= limit:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Try again later.",
        )

    requests.append(now)


@app.get(
    "/custom-sliding",
    dependencies=[Depends(custom_sliding_check)],
)
async def custom_sliding():
    return {
        "endpoint": "custom-sliding",
        "limit": "100 requests per minute",
    }


# 6. Unrestricted endpoint: no rate limiter.
@app.get("/unlimited")
async def unlimited():
    return {
        "endpoint": "unlimited",
        "rate_limited": False,
    }
