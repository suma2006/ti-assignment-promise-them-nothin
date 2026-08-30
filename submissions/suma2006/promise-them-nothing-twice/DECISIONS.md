# Architectural and Policy Decisions

## The CTO vs. Support Conflict
Engineering did not resolve a commercial conflict; it built a config-driven, time-boxed, expiring override, making pulling the lever auditable. To address the tension between the CTO's strict 429 requirement and Support's mandate for zero 429s during Northwind's 02:00–04:00 UTC batch window, Northwind is granted an elevated limit (1500 RPM) strictly during those hours, expiring entirely in 5 weeks.

We explicitly rejected the following alternatives:
- **Strict 300 RPM enforcement:** Guarantees Northwind's batch fails, which risks catastrophic churn.
- **Permanent capacity bump (1500 RPM):** Surrenders commercial leverage, permanently distorts capacity planning, and sets a poor precedent.
- **Shadow mode (soft limiting):** Directly violates the CTO's strict requirement for no soft warnings.

Crucially, the Support requirement for zero 429s (R10) is only probabilistically satisfied. A finite ceiling of 1500 RPM guarantees a 429 if the batch queue drives traffic to 1501 RPM. No finite ceiling guarantees zero 429s.

## Algorithm and Distributed Coordination
The system implements a sliding window log coordinated entirely via Redis using an atomic Lua script. Redis `TIME` serves as the sole clock for counting requests and resolving active policy windows, which strictly eliminates application node clock drift.

In a 3-node cluster with a 300 RPM limit, worst-case admitted requests in a 60-second window vary significantly by algorithm:
- Per-node counter, fixed window: 1800 (mirrored) or 600 (partitioned).
- Per-node counter, sliding window: 900 (mirrored) or 300 (partitioned).
- Shared store, fixed window: 600.
- **Shared store, sliding window log (Chosen): 300.**

If Redis is unreachable, the system degrades to a fail-closed `503 Service Unavailable` response. This was verified during Session 05 by explicitly stopping the Redis container and observing a 503 on a live request. Note that failing closed during the batch window will break Northwind's load, but that is a commercial decision that is not engineering's to make.

## What the Harness Proves
The load harness mathematically validates the maximum admitted requests over any continuous 60-second trailing window. 
- **S1 (Two 300 RPM customers):** Before 300; After exactly 300.
- **S2 (One 600 RPM customer):** Before 600; After exactly 300.
- **S3 (10x 3000 RPM vs 1x 300 RPM):** Before 1459 (10x) / 300 (1x); After exactly 300 / 300.
- **S4 (Boundary straddle burst):** Before 600; After exactly 300.
- **S5 (Node distribution):** Before 600 total admitted (200 per node across 3 nodes); After exactly 300.
- **S6 (Override window check):** Before N/A; After 300 (inactive window) and 1500 (active window).

## What the Harness Does NOT Prove
The harness provides mathematical boundary testing but does not guarantee production viability. It tests a single Redis instance; it does not prove behavior under Redis failover (Sentinel) or cluster partitioning, nor does it generate production-scale concurrency load against the Lua script. The system trusts `X-Customer-Id` as absolute truth—if this is spoofable upstream, the isolation guarantees are void. Furthermore, testing the active override window (S6) requires a completely separate configuration file (`policies.demo.yaml`); the default harness run cannot prove the time-transition logic on its own.

Most critically, the harness is only as trustworthy as its own assertions. Two significant defects were discovered by manual inspection during Session 05: tests could "PASS" while silently dropping traffic (because only physical dispatch was measured, not server admission), and the hardcoded assertions contradicted dynamically loaded limits. These defects were fixed, but they demonstrate that the harness evaluates exactly what it is programmed to evaluate. The flaws were caught by human inspection, not by any automated check, meaning the harness remains fundamentally susceptible to logical gaps in its testing assumptions.

## What I Would Build Next (4 Hours)
1. **Structural Logging:** Emit exact rate-limit metadata and limit resolutions per request to an ELK/Datadog pipeline to provide observable metrics across the cluster.
2. **Redis Sentinel Integration:** Introduce high-availability replication to prove the system can survive a primary node failure without triggering the fail-closed `503` outage across the platform.
3. **Retry-Amplification Harness Scenario:** Northwind's client amplifies on 429, which is the entire reason the override ceiling needs headroom above their observed p99. That argument is currently untested.
4. **Gateway-Signed Customer Identity:** Since `X-Customer-Id` spoofing is a known hole that voids isolation, integrating a cryptographically signed identity mechanism is essential.
