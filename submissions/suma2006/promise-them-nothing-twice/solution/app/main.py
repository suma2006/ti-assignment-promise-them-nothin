import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.config import get_customer_policy
from app.limiter.memory_fixed_window import MemoryFixedWindowLimiter
from app.limiter.redis_sliding_window import RedisSlidingWindowLimiter

app = FastAPI()
node_id = os.getenv("NODE_ID", "unknown-node")

# Select the limiter by env var, defaulting to redis
limiter_type = os.getenv("LIMITER_TYPE", "redis")
if limiter_type == "memory":
    limiter = MemoryFixedWindowLimiter()
else:
    limiter = RedisSlidingWindowLimiter()

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Exclude /healthz from rate limiting
    if request.url.path == "/healthz":
        response = await call_next(request)
        response.headers["X-Node-Id"] = node_id
        return response
        
    customer_id = request.headers.get("x-customer-id")
    if not customer_id:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing X-Customer-Id header"}
        )
        
    policy = get_customer_policy(customer_id)
    if not policy:
        return JSONResponse(
            status_code=400,
            content={"error": "Unknown customer id"}
        )
        
    try:
        allowed, limit, remaining, retry_after = limiter.check(policy)
    except RuntimeError as e:
        if str(e) == "Redis unavailable":
            response = JSONResponse(
                status_code=503,
                content={"error": "Service Unavailable"}
            )
            response.headers["X-Node-Id"] = node_id
            return response
        raise e
    
    if not allowed:
        response = JSONResponse(
            status_code=429,
            content={"error": "Too Many Requests"}
        )
        response.headers["Retry-After"] = str(retry_after)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-Node-Id"] = node_id
        return response
        
    # Allowed
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-Node-Id"] = node_id
    return response

@app.get("/api/v1/ping")
async def ping():
    return {"status": "ok", "message": "pong"}

@app.get("/healthz")
async def healthz():
    return {"status": "healthy"}
