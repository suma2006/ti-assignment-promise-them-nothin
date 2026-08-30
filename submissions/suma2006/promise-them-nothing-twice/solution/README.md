# RelayAPI Distributed Rate Limiter

This repository contains a fully distributed, sliding window log rate limiter implemented in Python (FastAPI) and Redis.

## Prerequisites

To run this build locally in under 15 minutes, you need:
- Docker and Docker Compose v2
- Python 3 (for the load harness)

## Quickstart

1. Stand up the infrastructure (3 app nodes, Nginx load balancer, Redis):
   ```bash
   make up
   ```
2. Run the load test harness to validate limits:
   ```bash
   make harness
   ```

## Make Demo

The default `make harness` command runs with the standard configuration, where Northwind's batch override window is inactive (enforcing 300 RPM). To test the active time-based override (1500 RPM), run:
```bash
make demo
```
This restarts the cluster using `config/policies.demo.yaml` (where the active window is set to 00:00-23:59, ensuring it is always active) and re-runs the harness. Setting a perpetually active window is the simplest way to demonstrate the active path without requiring time-shifting or clock manipulation. This demonstrates that S6 correctly admits exactly 1500 requests instead of 300.

## Harness Scenarios

Each scenario proves a specific requirement of the rate limiter:
- **S1:** Proves that multiple customers under quota do not interfere with each other.
- **S2:** Proves that a single customer is strictly capped at their limit under sustained overload.
- **S3:** Proves that a high-traffic customer cannot consume a low-traffic customer's budget (strict fairness).
- **S4:** Proves that traffic bursts crossing the minute boundary cannot artificially double the allowed limit.
- **S5:** Proves that a shared store constrains total admissions across nodes, where per-node state would not.
- **S6:** Proves that time-bound customer overrides dynamically evaluate based on the current time without code changes.

## Switching Limiters

The system includes a naive, in-memory fixed-window limiter (`memory_fixed_window.py`) to demonstrate exactly how uncoordinated rate limiters fail across distributed boundaries. It remains in the codebase as an educational baseline. 

You can toggle the implementation by modifying the `LIMITER_TYPE` environment variable in `docker-compose.yml` (`redis` or `memory`).

## Counting Semantics

*The following is extracted verbatim from the system design documentation:*

The rate limiter enforces a strict sliding window log algorithm utilizing Redis as a centralized coordination store.

*   **Counting and Evaluation:** Only accepted requests are added to the window log. Rejected requests (HTTP 429) are not counted, do not consume quota, and do not extend the backoff period. The system evaluates the trailing 60 seconds relative to the arrival time of each incoming request.
*   **Atomicity:** The entire evaluation cycle—fetching the current time, pruning expired requests, evaluating quota policy, and logging new requests—is executed within a single, atomic Redis Lua script. This prevents race conditions and ensures identical enforcement across all distributed app nodes.
*   **Limit Transitions:** Quota limit changes (e.g., from an override window opening or closing) are applied instantaneously. When a limit increases or decreases at a time boundary, the new limit is immediately enforced against the existing 60-second log of requests. A continuous 60-second span straddling a limit transition may therefore legitimately contain more admitted requests than the lower bound, but never more than the highest limit active during that span.
*   **Degraded Mode:** If the Redis coordination store becomes unreachable, the rate limiter fails closed, returning HTTP 503 Service Unavailable for all requests to prevent undefended overload of upstream services.

## Reproducing the Fail-Closed 503

The system intentionally fails closed to protect downstream resources. To verify this:
1. Ensure the system is running (`make up`).
2. Stop the Redis container:
   ```bash
   docker compose stop redis
   ```
3. Issue a request (it will return a `503 Service Unavailable`):
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" -H "X-Customer-Id: cust-s1-1" http://localhost:8080/api/v1/ping
   ```
4. Restore the system:
   ```bash
   docker compose start redis
   ```

## Configuration File Layout

Configuration is driven by a YAML file (e.g., `config/policies.yaml`). It maps tiers to base RPMs, assigns customers to tiers, and defines temporary overrides.

To add a new customer, append them to the `customers` block:
```yaml
customers:
  "new-customer-id":
    tier: growth
```

To add an override, append a new block to `overrides`:
```yaml
overrides:
  - override_id: "unique-uuid"
    customer_id: "new-customer-id"
    override_rpm: 2000
    window_start_utc: "14:00"
    window_end_utc: "16:00"
    expires_at_timestamp: 1791108808 # Epoch timestamp
    approved_by: "Approver Name"
    reason: "Reason for exception"
    ticket_ref: "TKT-5678"
```
