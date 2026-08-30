# CONTEXT

Living state of the build. Authoritative. Updated at the end of every session.

## What this is

Distributed per-customer rate limiter for RelayAPI (fictional B2B API platform).
Take-home assignment. See `../../../../../briefs/` for source memos.

## Current state

Skeleton API and naive limiter built and running. The environment consists of 3 load-balanced app nodes, Redis, and Nginx. The load harness has been built in `solution/harness/` to rigorously measure `max_admitted_in_any_trailing_60s`. The naive limiter has been systematically proven wrong against it.

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

Session 04 — Developed the async Python load harness and established the failure baseline for the naive limiter. Session 05 must beat these numbers to pass: S2 (600), S3 (1459), S4 (600), S5 (200/200/200 per node). See `solution/docs/handoffs/04-handoff.md` for the full record.
