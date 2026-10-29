
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from collections import defaultdict, deque
from threading import Lock, BoundedSemaphore
from time import monotonic, sleep
import json


# -----------------------------
# Rate limiter configuration
# -----------------------------

# 1. Fixed window: 3 requests per 10 seconds
FIXED_LIMIT = 3
FIXED_WINDOW = 10

# 2. Sliding window: 15 requests per 5 seconds
SLIDING_LIMIT = 15
SLIDING_WINDOW = 5

# 3. Token bucket: capacity 100, refill 10 per 5 seconds
TOKEN_CAPACITY = 100
TOKEN_REFILL = 10
TOKEN_REFILL_PERIOD = 5

# 4. Concurrency: maximum 5 simultaneous requests
CONCURRENCY_LIMIT = 5
concurrency_semaphore = BoundedSemaphore(CONCURRENCY_LIMIT)

# 5. Custom sliding window: 100 requests per minute
CUSTOM_LIMIT = 100
CUSTOM_WINDOW = 60

lock = Lock()
fixed_windows = {}
sliding_windows = defaultdict(deque)
token_buckets = {}

# Fixed Window Algorithm
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

# Sliding Window Algorithm 
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

# Token Bucket  Algorithm
def token_bucket_check(client):
    now = monotonic()

    with lock:
        tokens, last_update = token_buckets.get(
            client, (float(TOKEN_CAPACITY), now)
        )

        elapsed = now - last_update
        tokens = min(
            TOKEN_CAPACITY,
            tokens + elapsed * TOKEN_REFILL / TOKEN_REFILL_PERIOD,
        )

        if tokens < 1:
            token_buckets[client] = (tokens, now)
            return False

        token_buckets[client] = (tokens - 1, now)
        return True
    
# Custom Sliding Window Algorithm
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


# Rest API and endpoints

class RateLimitAPI(BaseHTTPRequestHandler):

    def send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def reject(self):
        self.send_json(429, {
            "error": "Too many requests. Please try again later."
        })

    def do_GET(self):
        client = self.client_address[0]
        path = self.path.split("?")[0]

        # Fixed Window endpoint
        if path == "/fixed":
            if not fixed_window_check(client):
                return self.reject()

            return self.send_json(200, {
                "endpoint": "fixed",
                "limit": "3 requests per 10 seconds"
            })

        # Sliding Window endpoint 
        elif path == "/sliding":
            if not sliding_window_check(client):
                return self.reject()

            return self.send_json(200, {
                "endpoint": "sliding",
                "limit": "15 requests per 5 seconds"
            })

        # Token Bucket Endpoint
        elif path == "/token":
            if not token_bucket_check(client):
                return self.reject()

            return self.send_json(200, {
                "endpoint": "token",
                "capacity": TOKEN_CAPACITY,
                "refill": "10 tokens per 5 seconds"
            })

        # Concurrency Limiter Endpoint
        elif path == "/concurrency":
            if not concurrency_semaphore.acquire(blocking=False):
                return self.reject()

            try:
                sleep(2)  # Simulate a long-running request.
                return self.send_json(200, {
                    "endpoint": "concurrency",
                    "max_concurrent_requests": CONCURRENCY_LIMIT
                })
            finally:
                concurrency_semaphore.release()

        # Custom Sliding Window Endpoint
        elif path == "/custom-sliding":
            if not custom_sliding_check(client):
                return self.reject()

            return self.send_json(200, {
                "endpoint": "custom-sliding",
                "limit": "100 requests per minute"
            })

        # Unrestricted endpoint
        elif path == "/unlimited":
            return self.send_json(200, {
                "endpoint": "unlimited",
                "rate_limited": False
            })

        else:
            return self.send_json(404, {
                "error": "Endpoint not found"
            })

    def log_message(self, format, *args):
        print(f"{self.client_address[0]} - {format % args}")


if __name__ == "__main__":
    server = ThreadingHTTPServer(
        ("127.0.0.1", 3100),
        RateLimitAPI
    )

    print("API running at http://127.0.0.1:3100")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()
