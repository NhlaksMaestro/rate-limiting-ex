# Rate Limiting API (Python standard library)

A small REST API built with Python's standard-library HTTP server. It demonstrates several rate-limiting strategies without a web framework or external packages.

## Requirements

- Python 3.7 or later

## Run

From this directory:

```powershell
py main.py
```

The API listens on `http://127.0.0.1:3100`. Stop it with `Ctrl+C`.

## Endpoints

| Method | Path | Behavior |
|---|---|---|
| GET | `/fixed` | Fixed window: 3 requests per 10 seconds |
| GET | `/sliding` | Sliding window: 15 requests per 5 seconds |
| GET | `/token` | Token bucket: capacity 100, refills 10 tokens every 5 seconds |
| GET | `/concurrency` | Allows at most 5 simultaneous requests; each takes about 2 seconds |
| GET | `/custom-sliding` | Sliding window: 100 requests per minute |
| GET | `/unlimited` | No rate limit |

Limited endpoints return HTTP `429 Too Many Requests` when a limit is exceeded. Unknown paths return `404`.

## Try it

```powershell
curl.exe http://127.0.0.1:3100/fixed
curl.exe http://127.0.0.1:3100/unlimited
```

Repeat a request to `/fixed` four or more times within 10 seconds to observe a `429` response. Requests from the same client IP share the same in-memory limits.

## Notes

All counters and token buckets are held in process memory. They reset when the server restarts and are not shared across multiple server processes. This project is intended to demonstrate rate-limiting algorithms, not to provide production-grade distributed rate limiting.
