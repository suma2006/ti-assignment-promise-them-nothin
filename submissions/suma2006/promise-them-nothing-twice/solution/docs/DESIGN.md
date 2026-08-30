# DESIGN

This document captures the architectural and policy decisions for the RelayAPI distributed rate limiter.

## 1. Resolution of Constraints (Pair 1)

**The Conflict:** R1 enforces a strict 429 at quota. R16 sets Northwind's quota at 300 RPM. R17 notes Northwind's batch is 800–1200 RPM. R10 demands zero 429s during this batch window (02:00–04:00 UTC).

**The Selected Resolution: The Time-Bound Bridge (Resolution 4)**
Extend the configuration schema to support time-of-day boundaries and absolute expiries. Grant Northwind an elevated limit (e.g., 1500 RPM) strictly between 02:00–04:00 UTC, expiring entirely in 5 weeks (before their renewal). Outside these bounds, strictly enforce the 300 RPM base contract.

*   **Satisfies:** **R1** (Hard enforcement of the active ceiling), **R9** (Config-driven exception path), **R12** (Exception is invisible to the customer), **R3** (Strictly fair, data-driven code path identical for all customers).
*   **Violates:** **R16 only**. The effective runtime limit formally diverges from the signed contract for two hours a day, but the built-in expiry ensures this divergence cannot become permanent without a new contract.
*   **Probabilistic Satisfaction:** **R10** is only probabilistically satisfied. A finite ceiling of 1500 RPM guarantees a 429 if the batch queue drives traffic to 1501 RPM. Absolute protection from 429s requires infinite capacity, which violates R1.
*   **Defense to the CTO (Priya):** "This uses the auditable config mechanism you required to resolve a commercial crisis, relying on trivial, stateless time-comparisons that protect our infrastructure today and automatically expire to force the contract renewal next month."

### Rejected Resolutions
1.  **Strict Contract Enforcement:** Set to 300 RPM. Rejected because it guarantees Northwind's batch fails, risking a catastrophic 60% ARR churn by ignoring the Support Lead's mandate (R10).
2.  **The Configured Capacity Bump:** Permanently bump Northwind to 1500 RPM. Rejected because it surrenders contractual leverage, permanently distorts capacity planning, and sets a precedent of giving away infrastructure for free.
3.  **Soft Limiting (Shadow Mode):** Log overages but never 429. Rejected because it directly violates Priya's non-negotiable rule (R1: "No soft warnings") and risks a noisy-neighbor platform outage due to lack of backpressure.

## 2. Algorithm Choice

**Algorithm:** Sliding Window Log (implemented via Redis Sorted Sets).

The test harness will verify the worst-case number of requests admitted in any trailing 60-second window across a 3-node cluster configured with a 300 RPM limit. The mathematical boundaries are established as follows:

| Strategy | Worst-Case Admitted in 60s | Reasoning |
| :--- | :--- | :--- |
| Per-node counter, fixed window | 1800 (if mirrored) or 600 (partitioned) | Edge-doubling boundary (00:59 and 01:00) × 3 uncoordinated nodes. |
| Per-node counter, sliding window | 900 (mirrored) or 300 (partitioned) | Sliding window prevents edge-doubling, but uncoordinated nodes multiply the quota. |
| Shared store, fixed window | 600 | Shared limit prevents node multiplication, but fixed window allows edge-doubling burst. |
| **Shared store, sliding window log** | **300** | **The chosen algorithm.** Shared state enforces the global limit; the trailing 60s log strictly prevents edge bursts. |

*Testable Claim:* The harness will demonstrate that our Sliding Window Log implementation never admits more than exactly the configured RPM within *any* continuous 60-second slice, regardless of load balancing distribution.

## 3. Coordination Mechanism

**Mechanism:** Redis with atomic Lua scripts.

*   **Sole Clock Source:** The rate limiter relies exclusively on the Redis server's internal OS clock (read via the `TIME` command within Lua). App node clocks are completely ignored for counting purposes. This centralized time authority eliminates the risk of distributed clock drift shifting window boundaries (Tension 3d).
*   **Race Condition Prevention:** The read-evaluate-write sequence is entirely encapsulated in a single Lua script. Because Redis executes scripts atomically in its single-threaded event loop, interleaved reads and writes are impossible. The counting is mathematically sound regardless of concurrent load.

## 4. Degraded Mode (Redis Unreachable)

**Policy:** Fail-Closed (returning `503 Service Unavailable`).

Returning a `429` during an infrastructure failure is factually untrue and actively dangerous. Because Northwind retries aggressively on `429`s (R18), returning one during a cache outage would weaponize their retry loop against us, transforming a caching failure into a localized DDoS on our app nodes. A `503` accurately reflects the state.

**Open Policy Decision:** 
Failing closed satisfies Priya's directive to prioritize quota integrity over availability (R6, R1). However, if Redis fails between 02:00–04:00 UTC, **Northwind's batch will break, violating R10**. 
*   *Decision Owner:* Priya (CTO) and Marcus (Support). 
*   *Alternative Cost:* If they mandate failing open specifically during the batch window to protect Northwind, they surrender R1 (hard quota) and risk a catastrophic platform outage if the unguarded load overwhelms the backend.

## 5. Override Config Schema

To satisfy R9 (config and audit) and R3 (strict fairness), commercial exceptions are handled via a generic, auditable config schema evaluated identically for every customer.

### Schema Fields
*   `override_id`: A stable UUID so admitted requests can explicitly trace back to the exact policy record that admitted them.
*   `customer_id`: Target customer.
*   `override_rpm`: The elevated limit.
*   `window_start_utc`: The daily opening bound (e.g., "02:00").
*   `window_end_utc`: The daily closing bound (e.g., "04:00").
*   `expires_at_timestamp`: Hard expiration date (e.g., 5 weeks out).
*   **Audit Fields:** `approved_by`, `reason`, `ticket_ref`.

### Evaluation Path
There is exactly one code path, evaluated identically for every customer on every request:
1.  Read base tier RPM.
2.  If an override record exists for the customer, AND `now` is between `window_start_utc` and `window_end_utc`, AND `now` < `expires_at_timestamp`, apply `override_rpm`.
3.  Otherwise, apply base tier RPM.

Northwind is simply one row of data in this system. There are no hidden bypasses or `if (customerId === "Northwind")` blocks. 

*Constraint Note:* We will **not** add a test-only clock override or a bypass header to trigger the window artificially. Such test hooks constitute the exact hidden bypasses R3 forbids. To demo the time window without waiting until 02:00 UTC, the config row itself must be parameterized—setting the window bounds relative to the demo's start time.

## 6. Counting Semantics (For Security Reviews)

"Our API strictly enforces your negotiated Request Per Minute (RPM) quota using a centralized, high-precision sliding window algorithm. We do not use fixed one-minute buckets that allow burst doubling at the top of the minute, nor do we approximate counts across disconnected nodes. Every request is recorded atomically and evaluated against the exact number of requests you have made in the trailing 60 seconds across our entire infrastructure. If your limit is 300 RPM, it is mathematically impossible for the system to admit 301 requests within any continuous 60-second span."

## 7. Open Questions and Accepted Risks

1.  **The Finite Ceiling Gamble:** The 1500 RPM override for Northwind is still a fixed guess. If their queue is unusually deep and hits 1501 RPM, the `429` triggers their aggressive retry loop (R18) and the batch fails. We cannot guarantee zero 429s without infinite capacity.
2.  **Boundary Jitter (Tension 3d):** While Redis centralizes time for quota evaluation, the app nodes evaluate the *config window* (e.g., is it 02:00 UTC yet?) locally before passing the target RPM to Redis. If Northwind's batch fires precisely on the second, and app node drift causes an evaluation at `01:59:59.9`, the request is checked against the 300 RPM limit. This yields a `429`, instantly triggering the retry loop just as the window opens.
3.  **Commercial Problems as Technical Solutions:** We are accepting the complexity of scheduling and TTL evaluation in a V1 rate limiter merely to bridge a commercial dispute until a contract renewal.
