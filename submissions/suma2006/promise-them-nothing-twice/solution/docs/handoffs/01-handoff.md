# Handoff — Session 01 (Framing)

---

## 1. What I asked for this session

Extract every hard requirement from the three source briefs, identify any pairs that cannot
be literally satisfied simultaneously, and surface secondary implementation tensions. No
code, no algorithm choice, no solution proposal.

---

## 2. What is now true that wasn't before

- `solution/docs/CONSTRAINTS.md` — created; 20 numbered requirements (Section 1), one
  irreconcilable pair with cited figures (Section 2), six secondary tensions (Section 3).
- `solution/docs/handoffs/01-handoff.md` — this file; created end-of-session.
- `solution/docs/CONTEXT.md` — updated from placeholder to reflect session 01 outcome.

---

## 3. What works, and how it was verified

No executable code was produced this session. The following command was run at end-of-session:

```
wc -l submissions/suma2006/promise-them-nothing-twice/solution/docs/CONSTRAINTS.md
```

Actual observed output: `169 submissions/suma2006/promise-them-nothing-twice/solution/docs/CONSTRAINTS.md`

(`wc -l` counts newlines; a file with a trailing newline reports one fewer than its line
count. The file has 169 lines.)

CONSTRAINTS.md was read end-to-end at end-of-session (see Section 4). All sections present
and structurally intact.

---

## 4. What is broken or unverified, and the visible symptom

- **CONSTRAINTS.md formatting:** read end-to-end at end-of-session. All six secondary
  tension sections (3(a)–3(f)) are present with correct headings and body text. No
  formatting regressions observed. This risk is closed.
- **No decisions are locked.** The single irreconcilable pair (Section 2, Pair 1) is
  documented but not resolved. No algorithm is chosen. No coordination mechanism is chosen.
  The design session has not started.
- **`solution/app/`, `solution/config/`, `solution/harness/`** directories exist but are
  empty. No code, no README, no docker-compose.

---

## 5. The single next action

Open a new session. Read `solution/docs/CONSTRAINTS.md` in full. Produce
`solution/docs/DESIGN.md` by resolving exactly Section 2, Pair 1: state explicitly
whether the config-driven exception path (R9) is exercised in favour of R10 (Marcus /
Northwind batch window), or whether R1 is held strictly (Priya / hard 429) and the business
consequence is documented. That decision gates every subsequent design choice. Do not pick
an algorithm or write code until the pair-1 resolution is written and confirmed.

---

## 6. Assumptions I made that you did not confirm

- **Enterprise-tier fairness scope.** I argued in 3(f) that R3's "same tier, same
  treatment" clause does not apply across Enterprise customers because the tier is defined
  as "custom — Negotiated" (R20), making per-customer differentiation the normal operating
  mode. You did not explicitly confirm this reasoning; you proceeded without objecting to
  it. If the argument is wrong, 3(f)'s framing needs revision before the design session.
- **CONTEXT.md as a living document.** I treated the existing CONTEXT.md as a placeholder
  to overwrite. If it was meant to accumulate sections rather than be replaced, the update
  approach in this handoff is wrong.
- **No DECISIONS.md yet.** I assumed DECISIONS.md does not exist and should be the primary
  output of session 02. If it was pre-populated elsewhere, that changes the next action.
