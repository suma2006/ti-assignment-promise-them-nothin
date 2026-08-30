# Handoff — Session 04 (Load Harness)

---

## 1. What I asked for this session

Build the load harness in `solution/harness/` using Python, `asyncio`, and `httpx`. The harness must prove the correctness or incorrectness of the rate limiter using `max_admitted_in_any_trailing_60s` as the headline metric, test 5 specific boundary and load scenarios, accurately drive concurrent load, and report the results in a stdout table.

---

## 2. What is now true that wasn't before

- `solution/harness/runner.py` created to drive concurrent HTTP load, calculate exact achieved dispatch RPMs, and evaluate the sliding 60-second window metric mathematically using precise send timestamps.
- `solution/Makefile` updated with a `harness` target that isolates `httpx` in a lightweight `.venv-harness` environment, avoiding pollution of the reviewer's laptop with service dependencies.
- The harness systematically executes and fails the naive limiter across S2-S5.

---

## 3. What works, and how it was verified

The harness correctly executes all 5 scenarios and accurately calculates exact metrics, validating its ability to trap limiter flaws. 

Observed output verifying the baseline failure:
```text
Starting load harness...
Running S1...
Running S2...
Running S3...
Running S4...
  [S4] Waiting 44.0s for UTC minute boundary...
  [S4] Minute boundary approaching: 11:02:00 UTC
  [S4 Diagnostics]
    - First request of half 1: 1788087718.047 UTC
    - First request of half 2: 1788087721.003 UTC
    - Computed boundary:       1788087720.000 UTC
    - Dispatched before boundary: 300
    - Dispatched after boundary:  300
    - Per-node admitted counts:   {'app2': 200, 'app1': 200, 'app3': 200}

Running S5...

==================================================================================================================================
ID   | STATUS  | SCENARIO                                 | TARGET RPM | ACHIEVED RPM | METRIC (Max 60s) | EXPECTED BOUND
----------------------------------------------------------------------------------------------------------------------------------
S1   | PASS    | Two growth customers at 300 RPM for 60s  | 300        | 301          | 300              | <= 300
S2   | FAIL    | One customer at 600 RPM for 60s          | 600        | 601          | 600              | <= 300
S3   | FAIL    | 10x limit vs 1x limit                    | 3000/300   | 3001/301     | 1459/300         | 10x: <= 300, 1x: <= 300 (0 rejects)
S4   | FAIL    | Boundary straddle (58s and 01s)          | BURST      | n/a (burst)  | 600              | <= 300
S5   | FAIL    | Node distribution check                  | 600        | 601          | 600              | <= 300
==================================================================================================================================

[S1] Details: Cust1 max: 300, Cust2 max: 300. NOTE: S1 passes only because 300 RPM does not exhaust the naive 300x3 per-node ceiling.
[S2] Details: Admitted: 600, 429s: 0
[S3] Details: 10x max: 1459, 1x max: 300, 1x rejects: 0. NOTE: 10x max (1459) exceeds 900 because the 60s run straddled a fixed-window boundary (3 nodes x 300 quota x 2 for boundary doubling).
[S4] Details: Boundary crossed at 11:02:00 UTC. Max admitted: 600. Burst size: 600, elapsed: 5.05s.
[S5] Details: Node admitted counts: {'app1': 200, 'app2': 200, 'app3': 200}

Harness failed due to scenario S2
make: *** [Makefile:15: harness] Error 1
```

---

## 4. What is broken or unverified

- The naive memory fixed-window limiter fails scenarios S2, S3, S4, and S5. **This is EXPECTED and is the point of this session.** The harness correctly flags these as failures.
- **S4 theoretical bound caveat**: In S4, we measure that all 600 requests sent were admitted (returning a metric of 600). While this is sufficient to mathematically prove the boundary flaw, 600 is simply the burst size, not the limiter's actual ceiling. The true theoretical naive max for that window is 1800 (3 nodes × 300 tier × 2 for boundary doubling).
- **Harness State Pollution**: Scenarios share customers and do not reset limiter state on the API nodes between runs. This previously caused a false `PASS` on S4 because it reused a customer whose limit was already exhausted by S3. This is a known harness property. We isolated S4 by pointing it to an untouched customer (`cust-nw-demo`).

---

## 5. The single next action

Implement the final Redis + Lua atomic sliding window log limiter and swap it into `app/main.py`. Use this load harness to mathematically prove that the new limiter correctly passes all five scenarios.

---

## 6. Assumptions I made that you did not confirm

- I assume you recognize the caveat around S1's `PASS`. It passes only because the scenario never reaches the flaw: a 300 RPM total rate distributed across 3 nodes averages 100 RPM per node, which never exhausts the naive per-node ceiling of 300. It is not evidence of correctness against the naive limiter.
