# Session 05 Handoff

## 1. Summary of Changes
- Implemented the distributed sliding window log limiter using Redis and an atomic Lua script.
- Configured dynamic config loading using the `CONFIG_PATH` environment variable.
- Refactored `harness/runner.py` to prevent state pollution by assigning unique customer IDs per scenario.
- Hardened `harness/runner.py` by ensuring test validity guards strictly account for all HTTP responses (200s and 429s) and dynamically calculate effective bounds from the loaded config.

## 2. Architecture Details
- **Coordination**: Uses Redis `EVALSHA` for atomic Lua script execution.
- **Clock Source**: Strict reliance on Redis `TIME` exclusively within the Lua script to provide a globally consistent clock, bypassing all application-level timestamps.
- **Data Structure**: Stores request timestamps as scores in a Redis Sorted Set, utilizing `ZREMRANGEBYSCORE` and `ZCARD` to cleanly slice and enforce the exact 60-second trailing window.

## 3. Evidence

### Redis TIME EVAL Proof
```text
$ docker compose exec redis redis-cli EVAL "local t = redis.call('TIME') return {t[1], t[2]}" 0
1) "1788094249"
2) "488751"
```

### 503 Fail-Closed Proof
```text
$ docker compose stop redis
$ curl -s -o /dev/null -w "%{http_code}\n" -H "X-Customer-Id: cust-s1-1" http://localhost:8080/api/v1/ping
503
$ docker compose start redis
```

### Final Tables

**make harness (policies.yaml - Default Limits)**
```text
==================================================================================================================================
ID   | STATUS  | SCENARIO                                 | TARGET RPM | ACHIEVED RPM | METRIC (Max 60s) | EXPECTED BOUND
----------------------------------------------------------------------------------------------------------------------------------
S1   | PASS    | Two growth customers at 300 RPM for 60s  | 300        | 300          | 300              | <= 300 / <= 300
S2   | PASS    | One customer at 600 RPM for 60s          | 600        | 601          | 300              | <= 300
S3   | PASS    | 10x limit vs 1x limit                    | 3000/300   | 3002/301     | 300/300          | 10x: <= 300, 1x: <= 300 (0 rejects)
S4   | PASS    | Boundary straddle (58s and 01s)          | BURST      | n/a (burst)  | 300              | <= 300
S5   | PASS    | Node distribution check                  | 600        | 600          | 300              | <= 300
S6   | PASS    | Override window check                    | 1500       | n/a          | 300              | <= 300 (Inactive)
==================================================================================================================================

[S1] Details: Limits: 300/300. Cust1 max: 300, Cust2 max: 300. Total: 600 (200: 600, 429: 0, Other: {})
[S2] Details: Limit: 300. Admitted: 300, 429s: 300. Total: 600 (200: 300, 429: 300, Other: {})
[S3] Details: Limits: 300/300. 10x max: 300, 1x max: 300, 1x rejects: 0. Total: 3300 (200: 600, 429: 2700, Other: {})
[S4] Details: Limit: 300. Boundary crossed at 12:35:00 UTC. Max admitted: 300. Burst size: 600, elapsed: 5.67s. Total: 600 (200: 300, 429: 300, Other: {})
[S5] Details: Limit: 300. Exact admitted counts reflect Nginx round-robin dispatching exactly 200 requests to each node, from which {'app1': 100, 'app2': 100, 'app3': 100} were admitted. Total: 600 (200: 300, 429: 300, Other: {})
[S6] Details: Inactive window confirmed (Limit: 300, Admitted: 300). To test active window, start the app with policies.demo.yaml (e.g. 'make demo'). Total: 1500 (200: 300, 429: 1200, Other: {})
```

**make demo (policies.demo.yaml - Active Override)**
```text
==================================================================================================================================
ID   | STATUS  | SCENARIO                                 | TARGET RPM | ACHIEVED RPM | METRIC (Max 60s) | EXPECTED BOUND
----------------------------------------------------------------------------------------------------------------------------------
S1   | PASS    | Two growth customers at 300 RPM for 60s  | 300        | 300          | 300              | <= 300 / <= 300
S2   | PASS    | One customer at 600 RPM for 60s          | 600        | 601          | 300              | <= 300
S3   | PASS    | 10x limit vs 1x limit                    | 3000/300   | 3001/301     | 300/300          | 10x: <= 300, 1x: <= 300 (0 rejects)
S4   | PASS    | Boundary straddle (58s and 01s)          | BURST      | n/a (burst)  | 300              | <= 300
S5   | PASS    | Node distribution check                  | 600        | 600          | 300              | <= 300
S6   | PASS    | Override window check                    | 1500       | n/a          | 1500             | <= 1500 (Active)
==================================================================================================================================

[S1] Details: Limits: 300/300. Cust1 max: 300, Cust2 max: 300. Total: 600 (200: 600, 429: 0, Other: {})
[S2] Details: Limit: 300. Admitted: 300, 429s: 300. Total: 600 (200: 300, 429: 300, Other: {})
[S3] Details: Limits: 300/300. 10x max: 300, 1x max: 300, 1x rejects: 0. Total: 3300 (200: 600, 429: 2700, Other: {})
[S4] Details: Limit: 300. Boundary crossed at 12:47:00 UTC. Max admitted: 300. Burst size: 600, elapsed: 5.05s. Total: 600 (200: 300, 429: 300, Other: {})
[S5] Details: Limit: 300. Exact admitted counts reflect Nginx round-robin dispatching exactly 200 requests to each node, from which {'app3': 100, 'app1': 100, 'app2': 100} were admitted. Total: 600 (200: 300, 429: 300, Other: {})
[S6] Details: Active window confirmed (Limit: 1500, Admitted: 1500). Total: 1500 (200: 1500, 429: 0, Other: {})
```

## 4. Known Issues & Unproven Assertions
- **Session 04 Baseline Comparison**:
  - **S2**: Successfully constrained from 600 (Session 04) to exactly 300.
  - **S3**: 10x customer constrained from 1459 (Session 04) to exactly 300.
  - **S4**: Burst spanning across the minute boundary constrained from 600 (Session 04) to exactly 300.
  - **S5**: Per-node round-robin quota leaks (200/200/200 per node) collapsed to a shared global state constraint of exactly 300 total (100/100/100).
- **Harness Defects Fixed**:
  - Found and fixed a testing defect where scenarios could fraudulently "PASS" by secretly losing or rejecting traffic since achieved RPM only measured the speed of physical dispatch, not admission. 
  - S4's previously hardcoded `<=` bounds contradicted the effective limits dynamically applied by `make demo`, forcing invalid assertions.
- **Unproven Assertions**:
  - The implementation relies on a single Redis node; failover/replication scenarios (e.g. Sentinel or Cluster mode behavior) have not been proven.
  - The Lua script has not been subjected to production-scale concurrency load testing (e.g., millions of members within a sorted set) and remains unproven under catastrophic network partitioning.

## 5. Next Steps
- Add structural logging to observe rate limits across services via an ELK or Datadog ingestion pipeline.
- Implement Redis replication and Sentinel configuration to ensure high-availability fault tolerance.

## 6. Sign-off
- Antigravity
