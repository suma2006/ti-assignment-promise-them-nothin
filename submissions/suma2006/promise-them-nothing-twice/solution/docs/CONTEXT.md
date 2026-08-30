# CONTEXT

Living state of the build. Authoritative. Updated at the end of every session.

## What this is

Distributed per-customer rate limiter for RelayAPI (fictional B2B API platform).
Take-home assignment. See `../../../../../briefs/` for source memos.

## Current state

The distributed sliding window log rate limiter is fully implemented and running across 3 app nodes, backed by Redis and an atomic Lua script. The environment configuration dynamically handles customer policy overrides. The load harness in `solution/harness/` has been hardened to prevent state pollution and explicitly validate status codes. The distributed limiter successfully passes all scenarios, strictly enforcing correct RPM limits regardless of load balancing or time boundaries.

## Locked decisions

The following decisions are locked and must not be re-opened by later sessions:
- **Pair 1 Resolution:** Resolution 4 (The Time-Bound Bridge) is selected.
- **Algorithm:** Sliding window log.
- **Coordination:** Redis + atomic Lua scripts.
- **Clock Source:** Redis internal `TIME` is the sole clock; app node clocks are ignored.
- **Degraded Mode:** Fail-closed returning `503 Service Unavailable`.
- **Exception Schema:** A generic, auditable override schema evaluated identically for every customer (no hardcoded bypasses, no test-only clock overrides).

## Open conflict requiring a decision before design can proceed

None. The design is locked.

## Last session

Session 05 — Hardened the load harness to track explicit status code distributions and dynamically enforce effective bounds. Proved the Redis sliding window limiter successfully constrains burst traffic, node leaks, and boundary straddling to exactly 300 RPM. See `solution/docs/handoffs/05-handoff.md` for the full record and evidence tables.
