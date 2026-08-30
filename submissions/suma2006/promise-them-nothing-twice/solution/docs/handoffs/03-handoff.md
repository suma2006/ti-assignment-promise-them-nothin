# Handoff — Session 03 (Skeleton & Naive Limiter)

---

## 1. What I asked for this session

Build the service skeleton (FastAPI, Nginx, Redis) and implement a deliberately naive rate limiter that will be proven wrong in the next session.

---

## 2. What is now true that wasn't before

- `solution/requirements.txt` — added dependencies for FastAPI, Uvicorn, and Pydantic
- `solution/Dockerfile` — added container definition for the API
- `solution/docker-compose.yml` — added 3 app nodes, Redis, and Nginx round-robin
- `solution/Makefile` — added make targets for up, down, logs
- `solution/nginx.conf` — added reverse proxy configuration
- `solution/config/policies.yaml` — added configuration for tiers, customers, and overrides
- `solution/app/config.py` — added typed policy parsing and validation rules
- `solution/app/limiter/__init__.py` — created empty module
- `solution/app/limiter/base.py` — added `RateLimiter` ABC that passes raw properties instead of evaluated limits
- `solution/app/limiter/memory_fixed_window.py` — added the naive memory fixed-window baseline limiter
- `solution/app/main.py` — added FastAPI application with rate limiting middleware

---

## 3. What works, and how it was verified

The infrastructure and basic routing are functional.

**Containers running:**
```
$ docker compose ps
NAME               IMAGE            COMMAND                  SERVICE   CREATED          STATUS          PORTS
solution-app1-1    solution-app1    "uvicorn app.main:ap…"   app1      19 seconds ago   Up 17 seconds   8000/tcp
solution-app2-1    solution-app2    "uvicorn app.main:ap…"   app2      19 seconds ago   Up 17 seconds   8000/tcp
solution-app3-1    solution-app3    "uvicorn app.main:ap…"   app3      19 seconds ago   Up 17 seconds   8000/tcp
solution-nginx-1   nginx:alpine     "/docker-entrypoint.…"   nginx     6 minutes ago    Up 6 minutes    0.0.0.0:8080->80/tcp, [::]:8080->80/tcp
solution-redis-1   redis:7-alpine   "docker-entrypoint.s…"   redis     6 minutes ago    Up 6 minutes    0.0.0.0:6379->6379/tcp, [::]:6379->6379/tcp
```

**Round-robin verification:**
```
$ curl -s -i http://localhost:8080/healthz | grep x-node-id
x-node-id: app2
$ curl -s -i http://localhost:8080/healthz | grep x-node-id
x-node-id: app1
$ curl -s -i http://localhost:8080/healthz | grep x-node-id
x-node-id: app3
```

**400/400/200 Checks:**
```
$ curl -s -i http://localhost:8080/api/v1/ping
HTTP/1.1 400 Bad Request
...
{"error":"Missing X-Customer-Id header"}

$ curl -s -i http://localhost:8080/api/v1/ping -H "X-Customer-Id: unknown"
HTTP/1.1 400 Bad Request
...
{"error":"Unknown customer id"}

$ curl -s -i http://localhost:8080/healthz
HTTP/1.1 200 OK
...
{"status":"healthy"}
```

**400-Request Burst Test (via python script):**
```
$ python3 test_burst.py
Time: 0.58s
Status codes: {200: 400}
Node counts: {'app1': 134, 'app3': 133, 'app2': 133}
```

---

## 4. What is broken or unverified

The naive limiter being wrong is INTENTIONAL (designed behavior). The burst test above shows 400/400 requests admitted at a 300 RPM limit. Through a rapid sequential burst, the requests were spread evenly across the cluster (~133 requests per node). This confirms over-admission, but it does NOT isolate which of the three failure modes caused it — no node reached its own 300 ceiling and no window boundary was crossed. Isolating them is the harness's job.

---

## 5. The single next action

Build the test harness to systematically fire requests, assert against mathematical boundaries, and isolate exactly which failure modes the naive limiter violates. Once proven, swap the naive limiter for the Redis sliding window log implementation and use the same harness to prove the correctness.

---

## 6. Assumptions I made that you did not confirm

- I assumed Nginx should listen on standard HTTP port 80 internally and map to `8080` externally on the host.
- I assumed a short python script output was acceptable to demonstrate the 400 request sequential curl execution and distribution.
- I assumed you want the `__init__.py` files to just be empty for standard python module resolution.
