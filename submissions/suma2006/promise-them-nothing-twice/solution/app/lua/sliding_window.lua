local key = KEYS[1]
local request_id = ARGV[1]
local base_rpm = tonumber(ARGV[2])
local override_rpm = tonumber(ARGV[3])
local window_start = tonumber(ARGV[4])
local window_end = tonumber(ARGV[5])
local expires_at = tonumber(ARGV[6])
local policy_override_id = ARGV[7]

-- 1. Get current time from Redis
local time = redis.call('TIME')
local current_s = tonumber(time[1])
local current_ms = current_s * 1000 + math.floor(tonumber(time[2]) / 1000)

-- 2. Resolve active limit and policy ID
local effective_limit = base_rpm
local active_policy_id = "base"

local valid_expiry = (expires_at == -1) or (current_s < expires_at)

if override_rpm >= 0 and valid_expiry then
    local current_tod_s = current_s % 86400
    local in_window = false
    if window_start <= window_end then
        in_window = (current_tod_s >= window_start) and (current_tod_s < window_end)
    else
        in_window = (current_tod_s >= window_start) or (current_tod_s < window_end)
    end
    
    if in_window then
        effective_limit = override_rpm
        active_policy_id = policy_override_id
    end
end

-- 3. Prune entries older than 60s
local window_start_ms = current_ms - 60000
redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start_ms)

-- 4. Count existing entries
local current_count = redis.call('ZCARD', key)

-- 5. Admit or reject
local allowed = 0
local remaining = 0
local retry_after_ms = 0

if current_count < effective_limit then
    allowed = 1
    redis.call('ZADD', key, current_ms, request_id)
    remaining = effective_limit - current_count - 1
    redis.call('PEXPIRE', key, 60000)
else
    allowed = 0
    remaining = 0
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    if oldest and oldest[2] then
        retry_after_ms = tonumber(oldest[2]) + 60000 - current_ms
        if retry_after_ms < 0 then retry_after_ms = 0 end
    else
        retry_after_ms = 60000
    end
end

return {allowed, effective_limit, remaining, retry_after_ms, active_policy_id}
