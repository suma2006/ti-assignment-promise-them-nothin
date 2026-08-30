"""
Naive Memory Fixed-Window Rate Limiter.

This is a DELIBERATELY NAIVE baseline implementation and is incorrect for three reasons:
1. Per-node state: It maintains counts locally in the node's memory, meaning a 3-node cluster admits 3x the quota.
2. Boundary doubling: It uses fixed wall-clock buckets, allowing 2x the quota to burst across the top of the minute.
3. Node-local time evaluation: It evaluates the time-bound config (overrides) using the app node's local clock, re-introducing boundary jitter.
"""

import time
from typing import Tuple, Dict
from app.limiter.base import RateLimiter
from app.config import CustomerPolicy

class MemoryFixedWindowLimiter(RateLimiter):
    def __init__(self):
        # State format: { customer_id: { "window": int, "count": int } }
        self.state: Dict[str, Dict[str, int]] = {}

    def _get_effective_limit(self, policy: CustomerPolicy) -> int:
        if not policy.override_id:
            return policy.base_rpm
            
        now_ts = int(time.time())
        if policy.expires_at_timestamp and now_ts >= policy.expires_at_timestamp:
            return policy.base_rpm
            
        def parse_hhmm_to_seconds(hhmm: str) -> int:
            h, m = map(int, hhmm.split(':'))
            return h * 3600 + m * 60
            
        # These fields are guaranteed by config validation if override_id exists
        start_secs = parse_hhmm_to_seconds(policy.window_start_utc)
        end_secs = parse_hhmm_to_seconds(policy.window_end_utc)
        
        current_time = time.gmtime(now_ts)
        tod_secs = current_time.tm_hour * 3600 + current_time.tm_min * 60 + current_time.tm_sec
        
        if start_secs < end_secs:
            if start_secs <= tod_secs < end_secs:
                return policy.override_rpm
        else:
            if tod_secs >= start_secs or tod_secs < end_secs:
                return policy.override_rpm
                
        return policy.base_rpm

    def check(self, policy: CustomerPolicy) -> Tuple[bool, int, int, int]:
        now = int(time.time())
        current_window = now // 60
        
        limit = self._get_effective_limit(policy)
        
        customer_state = self.state.get(policy.customer_id, {"window": current_window, "count": 0})
        
        if customer_state["window"] != current_window:
            customer_state = {"window": current_window, "count": 0}
            
        if customer_state["count"] < limit:
            customer_state["count"] += 1
            self.state[policy.customer_id] = customer_state
            remaining = limit - customer_state["count"]
            return True, limit, remaining, 0
            
        # Rate limited
        remaining = 0
        retry_after = 60 - (now % 60)
        return False, limit, remaining, retry_after
