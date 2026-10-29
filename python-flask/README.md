# Rate Limiting API (Flask)

A Flask REST API demonstrating fixed-window, sliding-window, token-bucket, and concurrency limits. Rate-limit state is held in memory.

## Requirements
- windows OS
- Python 3.9 or later
- Flask

The existing `requirements.txt` does not list Flask, so install Flask explicitly:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install Flask
```

## Run

From this directory:

```powershell
py app.py
```

The API listens on `http://127.0.0.1:5000`. Stop it with `Ctrl+C`.

## Endpoints

| Method | Path | Behavior |
|---|---|---|
| GET | `/fixed` | Fixed window: 3 requests per 10 seconds |
| GET | `/sliding` | Sliding window: 15 requests per 5 seconds |
| GET | `/token` | Token bucket: capacity 100, refills 10 tokens every 5 seconds |
| GET | `/concurrency` | Allows at most 5 simultaneous requests; each takes about 2 seconds |
| GET | `/custom-sliding` | Sliding window: 100 requests per minute |
| GET | `/unlimited` | No rate limit |

Limited endpoints return HTTP `429 Too Many Requests` when a limit is exceeded. The response body contains an error message.

## Try it

```powershell
curl.exe http://127.0.0.1:5000/fixed
curl.exe http://127.0.0.1:5000/unlimited
```

Repeat a request to `/fixed` four or more times within 10 seconds to observe a `429` response. Requests from the same client IP share the same in-memory limits.

## Notes

The counters and token buckets reset when the process restarts and are not shared across multiple server processes. Use a shared storage backend and a production WSGI server for a production deployment.
