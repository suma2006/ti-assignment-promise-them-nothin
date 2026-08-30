# CONTEXT

Living state of the build. Authoritative. Updated at the end of every session.

## What this is

Distributed per-customer rate limiter for RelayAPI (fictional B2B API platform).
Take-home assignment. See `../../../../../briefs/` for source memos.

## Current state

Design complete. `solution/docs/DESIGN.md` documents the architecture, policies, and testable claims.
No code written yet. `solution/app/`, `solution/config/`, `solution/harness/` directories exist and are empty.

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

Session 02 — design phase. Produced `solution/docs/DESIGN.md` resolving the primary constraint conflict and locking the technical architecture. See `solution/docs/handoffs/02-handoff.md` for full account of what was done, what is unverified, and the next action.
