# Rate Limiting API (FastAPI + Redis)

A FastAPI REST API that demonstrates Redis-backed rate limiting alongside in-memory examples of common rate-limiting algorithms.

## Requirements

- Python 3.9 or later
- A Redis server (the SDK defaults to `localhost:6379`)

Install the application dependencies in a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The `requirements.txt` file pins the FastAPI, Redis SDK, Redis client, Uvicorn, and their supporting dependencies.

## Redis configuration

Start Redis locally on its default address before using `/fixed`, or configure a different Redis URL using the SDK's `REDIS_URL` setting:

```powershell
$env:REDIS_URL = "redis://localhost:6379/0"
```

## Run

From this directory:

```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

The API listens on `http://127.0.0.1:8000`. Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Endpoints

| Method | Path | Limiter | Behavior |
|---|---|---|---|
| GET | `/fixed` | Redis-backed SDK | 3 requests per 10 seconds |
| GET | `/sliding` | In-memory | 15 requests per 5 seconds |
| GET | `/token` | In-memory | Capacity 100, refills 10 tokens every 5 seconds |
| GET | `/concurrency` | In-memory | At most 5 simultaneous requests; each takes about 2 seconds |
| GET | `/custom-sliding` | In-memory | 100 requests per minute |
| GET | `/unlimited` | None | No rate limit |

Rate-limited endpoints reject excess requests with HTTP `429 Too Many Requests`.

## Try it

```powershell
curl.exe http://127.0.0.1:8000/fixed
curl.exe http://127.0.0.1:8000/sliding
curl.exe http://127.0.0.1:8000/unlimited
```

Repeat a request to `/fixed` four or more times within 10 seconds to exercise the Redis-backed limit. The in-memory examples key their counters by client IP and reset when the application restarts; they are not shared across multiple workers or application instances.

## Notes

The Redis-backed `/fixed` limit can share state through Redis, while the other algorithm demonstrations keep state in the application process. Do not treat this mixed setup as a production rate-limiting configuration without considering worker coordination, client identification, Redis availability, and deployment settings.
