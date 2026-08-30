# CONTEXT

Living state of the build. Authoritative. Updated at the end of every session.

## What this is

Distributed per-customer rate limiter for RelayAPI (fictional B2B API platform).
Take-home assignment. See `../../../../../briefs/` for source memos.

## Current state

Framing complete. `solution/docs/CONSTRAINTS.md` is the only substantive output.
No code written. No algorithm chosen. No coordination mechanism chosen. No decisions locked.

`solution/app/`, `solution/config/`, `solution/harness/` directories exist and are empty.

## Locked decisions

None.

## Open conflict requiring a decision before design can proceed

**Section 2, Pair 1 of CONSTRAINTS.md:** Northwind's contracted limit is 300 RPM (R16).
Their nightly batch runs at 800–1200 RPM (R17). The CTO requires a 429 at quota (R1).
The support lead requires zero 429s during the batch window (R10). These cannot both be
literally true. The config-driven exception path (R9) exists and is permitted, but
exercising it is a decision that has not been made. This is the gate for session 02.

## Last session

Session 01 — framing only. Produced `solution/docs/CONSTRAINTS.md` (20 requirements,
1 irreconcilable pair, 6 secondary tensions). See `solution/docs/handoffs/01-handoff.md`
for full account of what was done, what is unverified, and the next action.
