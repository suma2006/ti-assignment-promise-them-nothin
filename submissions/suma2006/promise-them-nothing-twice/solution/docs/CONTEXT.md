# CONTEXT

Living state of the build. Authoritative. Updated at the end of every session.

## What this is

Distributed per-customer rate limiter for RelayAPI (fictional B2B API platform).
Take-home assignment. See `../../../../../briefs/` for source memos.

## Current state

Skeleton API and naive limiter built and running. The environment consists of 3 load-balanced app nodes, Redis, and Nginx. The naive limiter intentionally over-admits (e.g., admitting 400/400 requests against a 300 RPM limit due to uncoordinated node state). The `solution/harness/` directory is still empty.

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

Session 03 — API skeleton and baseline limiter. Config validation rules were tightened. A deliberately naive memory fixed-window limiter was implemented and demonstrated to over-admit traffic across nodes. See `solution/docs/handoffs/03-handoff.md` for the full record.
