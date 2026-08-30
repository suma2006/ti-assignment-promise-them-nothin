import os
import uuid
from typing import Tuple
from redis import Redis, RedisError
from redis.exceptions import NoScriptError
from app.limiter.base import RateLimiter
from app.config import CustomerPolicy

class RedisSlidingWindowLimiter(RateLimiter):
    def __init__(self):
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis = Redis(host=redis_host, port=redis_port, decode_responses=True)
        
        # Load Lua script
        lua_path = os.path.join(os.path.dirname(__file__), "../lua/sliding_window.lua")
        with open(lua_path, "r") as f:
            self.lua_script = f.read()
            
        self.script_sha = None

    def _load_script(self):
        if not self.script_sha:
            self.script_sha = self.redis.script_load(self.lua_script)
        return self.script_sha

    def check(self, policy: CustomerPolicy) -> Tuple[bool, int, int, int]:
        try:
            sha = self._load_script()
            key = f"rate_limit:{policy.customer_id}"
            request_id = str(uuid.uuid4())
            
            override_rpm = policy.override_rpm if policy.override_rpm is not None else -1
            
            window_start_utc = -1
            window_end_utc = -1
            if policy.window_start_utc and policy.window_end_utc:
                try:
                    start_h, start_m = map(int, policy.window_start_utc.split(":"))
                    window_start_utc = start_h * 3600 + start_m * 60
                    
                    end_h, end_m = map(int, policy.window_end_utc.split(":"))
                    window_end_utc = end_h * 3600 + end_m * 60
                except ValueError:
                    pass
            
            expires_at = policy.expires_at_timestamp if policy.expires_at_timestamp is not None else -1
            policy_override_id = policy.override_id if policy.override_id else ""
            
            args = [
                request_id,
                policy.base_rpm,
                override_rpm,
                window_start_utc,
                window_end_utc,
                expires_at,
                policy_override_id
            ]
            
            try:
                result = self.redis.evalsha(sha, 1, key, *args)
            except NoScriptError:
                self.script_sha = self.redis.script_load(self.lua_script)
                result = self.redis.evalsha(self.script_sha, 1, key, *args)
                
            allowed, effective_limit, remaining, retry_after_ms, active_policy_id = result
            
            retry_after_sec = max(1, int((retry_after_ms + 999) // 1000))
            
            return bool(allowed), int(effective_limit), int(remaining), retry_after_sec
            
        except RedisError as e:
            raise RuntimeError("Redis unavailable") from e
