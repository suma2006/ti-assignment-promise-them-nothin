import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.config import get_customer_policy
from app.limiter.memory_fixed_window import MemoryFixedWindowLimiter

app = FastAPI()
node_id = os.getenv("NODE_ID", "unknown-node")

# Instantiate the naive limiter for this session
limiter = MemoryFixedWindowLimiter()

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
        
    allowed, limit, remaining, retry_after = limiter.check(policy)
    
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
