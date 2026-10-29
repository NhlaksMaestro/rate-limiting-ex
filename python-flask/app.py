
from flask import Flask, jsonify, request
from collections import defaultdict, deque
from threading import Lock, BoundedSemaphore
from time import monotonic, sleep

app = Flask(__name__)

# Rate-limit configuration
FIXED_LIMIT = 3
FIXED_WINDOW = 10

SLIDING_LIMIT = 15
SLIDING_WINDOW = 5

TOKEN_CAPACITY = 100
TOKEN_REFILL = 10
TOKEN_REFILL_PERIOD = 5

CONCURRENCY_LIMIT = 5

CUSTOM_LIMIT = 100
CUSTOM_WINDOW = 60

# In-memory state
lock = Lock()
fixed_windows = {}
sliding_windows = defaultdict(deque)
token_buckets = {}

concurrency_semaphore = BoundedSemaphore(CONCURRENCY_LIMIT)


def client_key():
    # Use the client's IP address as the rate-limit key.
    return request.remote_addr or "unknown"


# 1. Fixed Window: 3 requests per 10 seconds
def fixed_window_check(client):
    now = monotonic()

    with lock:
        start, count = fixed_windows.get(client, (now, 0))

        if now - start >= FIXED_WINDOW:
            start, count = now, 0

        if count >= FIXED_LIMIT:
            return False

        fixed_windows[client] = (start, count + 1)
        return True


# 2. Sliding Window: 15 requests per 5 seconds
def sliding_window_check(client):
    now = monotonic()

    with lock:
        requests = sliding_windows[("sliding", client)]

        while requests and now - requests[0] >= SLIDING_WINDOW:
            requests.popleft()

        if len(requests) >= SLIDING_LIMIT:
            return False

        requests.append(now)
        return True


# 3. Token Bucket: capacity 100, refill 10 every 5 seconds
def token_bucket_check(client):
    now = monotonic()

    with lock:
        tokens, last_update = token_buckets.get(
            client, (float(TOKEN_CAPACITY), now)
        )

        elapsed = now - last_update
        tokens = min(
            TOKEN_CAPACITY,
            tokens + elapsed * TOKEN_REFILL / TOKEN_REFILL_PERIOD
        )

        if tokens < 1:
            token_buckets[client] = (tokens, now)
            return False

        token_buckets[client] = (tokens - 1, now)
        return True


# 5. Custom Sliding Window: 100 requests per minute
def custom_sliding_check(client):
    now = monotonic()

    with lock:
        requests = sliding_windows[("custom", client)]

        while requests and now - requests[0] >= CUSTOM_WINDOW:
            requests.popleft()

        if len(requests) >= CUSTOM_LIMIT:
            return False

        requests.append(now)
        return True


# 1. Fixed Window endpoint
@app.get("/fixed")
def fixed():
    if not fixed_window_check(client_key()):
        return jsonify(error="Too many requests. Try again later."), 429

    return jsonify(
        endpoint="fixed",
        limit="3 requests per 10 seconds"
    )


# 2. Sliding Window endpoint
@app.get("/sliding")
def sliding():
    if not sliding_window_check(client_key()):
        return jsonify(error="Too many requests. Try again later."), 429

    return jsonify(
        endpoint="sliding",
        limit="15 requests per 5 seconds"
    )


# 3. Token Bucket endpoint
@app.get("/token")
def token():
    if not token_bucket_check(client_key()):
        return jsonify(error="Token bucket exhausted. Try again later."), 429

    return jsonify(
        endpoint="token",
        capacity=TOKEN_CAPACITY,
        refill="10 tokens every 5 seconds"
    )


# 4. Concurrency endpoint
@app.get("/concurrency")
def concurrency():
    if not concurrency_semaphore.acquire(blocking=False):
        return jsonify(error="Maximum concurrent requests reached."), 429

    try:
        sleep(2)  # Simulate work taking two seconds.

        return jsonify(
            endpoint="concurrency",
            max_concurrent_requests=CONCURRENCY_LIMIT
        )
    finally:
        concurrency_semaphore.release()


# 5. Custom Sliding Window endpoint
@app.get("/custom-sliding")
def custom_sliding():
    if not custom_sliding_check(client_key()):
        return jsonify(error="Too many requests. Try again later."), 429

    return jsonify(
        endpoint="custom-sliding",
        limit="100 requests per minute"
    )


# 6. Unrestricted endpoint
@app.get("/unlimited")
def unlimited():
    return jsonify(
        endpoint="unlimited",
        rate_limited=False
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, threaded=True)
