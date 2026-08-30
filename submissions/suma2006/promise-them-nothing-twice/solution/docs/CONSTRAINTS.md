# CONSTRAINTS.md

Constraint analysis for the RelayAPI distributed rate limiter.
Sources: CTO memo (Priya Nair, 2026-03-14), Support Lead memo (Marcus Webb, 2026-03-14),
Platform Context (engineering wiki excerpt).

No solution is proposed here. Conflicts are documented precisely so that a later design
session can resolve them with full awareness of what is being traded away.

---

## 1. Hard Requirements

The table below captures every requirement stated across the three source documents.
"Absolute" means the source document uses language that admits no exception ("never",
"must", "non-negotiable"). "Preference" means the requirement is directional but the
document acknowledges a degree of flexibility or context-dependence.

| # | Requirement | Source | Type |
|---|-------------|--------|------|
| R1 | When a customer hits their RPM limit, return `429 Too Many Requests` with a `Retry-After` header. No soft warnings, no "bill you extra" path in v1. | CTO memo — §Requirements, bullet 1 | **Absolute** |
| R2 | Customer A's traffic spike must not consume Customer B's budget. Shared pools are out. | CTO memo — §Requirements, bullet 2 | **Absolute** |
| R3 | "Two customers on the same tier must get the same treatment. No hidden bypasses, no manual overrides in code paths that production traffic hits." | CTO memo — §Requirements, bullet 3 | **Absolute** |
| R4 | The system must be auditable: able to explain to an enterprise prospect "exactly how we counted their requests." | CTO memo — §Requirements, bullet 4 | **Absolute** |
| R5 | The implementation must work correctly when requests land on different nodes between seconds (3 stateless nodes, round-robin LB, no shared memory). | CTO memo — §Technical context | **Absolute** |
| R6 | Error direction must be under-limiting, not over-limiting: "I would rather reject a few extra legitimate requests than let someone blow past quota because nodes disagreed." | CTO memo — §Technical context | Preference (stated direction, not a hard bound) |
| R7 | Use a well-understood algorithm. No bespoke counter unless provably correct. | CTO memo — §Technical context | Preference |
| R8 | "We'll fix distributed state in v2" is not acceptable for GA. Distributed correctness is required at launch. | CTO memo — §What I do not want | **Absolute** |
| R9 | Commercial exceptions, if granted, must go through config and audit — "not a midnight commit." Hardcoded `if (customerId === ...)` blocks in production code paths are forbidden. | CTO memo — §What I do not want, final bullet | **Absolute** (mechanism constraint, not a prohibition on exceptions) |
| R10 | "Northwind must never see a 429 during their batch window." Batch window: 02:00–04:00 UTC nightly. | Support Lead memo — §What I need | **Absolute** (as stated; authority vs. CTO's authority is unresolved) |
| R11 | Do not ask Northwind to reschedule or spread requests. "Their ERP controls the schedule; we do not." | Support Lead memo — §My ask | **Absolute** (as stated) |
| R12 | Any exception mechanism must be "invisible to the customer. They should not see errors while we figure out a commercial arrangement." | Support Lead memo — §My ask | **Absolute** (as stated) |
| R13 | The system runs on 3 stateless app nodes behind a round-robin load balancer. No sticky sessions. | Platform context — §Traffic and topology | Absolute (infrastructure fact) |
| R14 | Redis is listed as an existing platform data store but "**may or may not** be available in your slice; do not assume ops will provision new infra for a prototype." This constrains *who provisions it*: the prototype cannot depend on ops to stand up Redis externally. A self-contained deployment (e.g. docker-compose with a Redis container) satisfies the constraint; an externally-managed Redis instance that requires ops action does not. The platform-context GA definition explicitly permits containers as a simulation mechanism. | Platform context — §Traffic and topology | Preference (deployment-scoping constraint on ops dependency; does not prohibit Redis or a shared store) |
| R15 | Customer identity is conveyed via `X-Customer-Id` header, described as "trusted from API gateway today." | Platform context — §Traffic and topology | Absolute (current architecture fact) |
| R16 | Northwind's contracted limit is **300 RPM** (Enterprise tier). | Platform context — §Northwind Logistics | Absolute (contract fact) |
| R17 | Northwind's actual nightly batch load is **800–1200 RPM** sustained for **90–120 minutes**. | Platform context — §Northwind Logistics | Absolute (observed traffic fact) |
| R18 | Northwind retries aggressively on 429. Retries on 429 amplify load. | Platform context — §Northwind Logistics | Absolute (observed behavior fact) |
| R19 | Northwind will not re-architect their scheduler before renewal (six weeks). | Platform context — §Northwind Logistics | Absolute (stated by Northwind) |
| R20 | Enterprise tier is defined as "custom — Negotiated." Per-customer limits within Enterprise are individualized by design, not shared. | Platform context — §Customer tiers | Absolute (tier definition fact) |

---

## 2. Irreconcilable Pairs

This section contains requirements that cannot both be literally satisfied. No reconciliation
is proposed. Each entry states the specific numbers or phrases that make simultaneous
satisfaction impossible.

### Pair 1 — Hard quota enforcement vs. Northwind batch window (R1 / R16 / R17 vs. R10)

**R1** requires that any customer exceeding their RPM limit receives a 429.
**R16** states Northwind's contracted limit is **300 RPM**.
**R17** states Northwind's nightly batch runs at **800–1200 RPM** — between **2.7× and 4× their contracted limit** — sustained for **90–120 minutes**.
**R10** states "Northwind must never see a 429 during their batch window."

For all three requirements to hold simultaneously, the system would need to:
- enforce 300 RPM as a hard ceiling (R1 + R16), and
- admit 800–1200 RPM without issuing a 429 (R10 + R17).

These cannot both be true. Any request rate above 300 RPM that is admitted without a 429
is, by definition, a violation of R1 as stated. Any 429 issued during the batch window is,
by definition, a violation of R10 as stated.

R9 explicitly permits a config-and-audit exception path, which can admit Northwind above
their contracted limit — but exercising that path resolves the conflict by choosing one
side. It does not make both requirements simultaneously true; it makes R10 take precedence
over R1 for Northwind during the batch window. That is a design decision, documented here
as required, not made here.

---

## 3. Secondary Tensions

These are not logical impossibilities. They are implementation-level collisions that will
force a choice during design or coding. Each is stated as a tension between two specific
things, not between the memos in the abstract.

### 3(a) — Under-limiting preference + retry amplification feedback loop (R6 vs. R18)

R6 states the preferred error direction: reject a few extra legitimate requests rather than
let a burst through. This is the conservative, quota-safe choice. R18 states that Northwind
retries aggressively on 429. A correct implementation honoring R6 — one that issues 429s
at or just below quota — triggers exactly the retry behavior that amplifies inbound load
further above quota. The more faithfully R6 is implemented for Northwind, the worse the
load spike R17 describes becomes. This is a feedback loop, not an impossibility: both facts
can be simultaneously true. But a design that ignores R18 while honoring R6 will produce
measurably worse outcomes than one that accounts for both.

### 3(b) — Coordination store failure mode: fail-open vs. fail-closed (R14 / R5 / R1 / R4)

R14, correctly read, does not prohibit a shared coordination store — it prohibits depending
on ops to provision one externally. A self-contained deployment (e.g. docker-compose
including Redis) is explicitly within scope. The tension here is not about whether a shared
store may be used, but about what the rate limiter does if that store becomes unavailable
at runtime after deployment.

No document states a degraded-mode behavior. Two implementation choices exist, neither
documented:

- **Fail-open** (admit all requests when the store is unreachable): satisfies availability
  but violates R5 — nodes act independently, effective quota becomes 3× the intended limit
  (one local counter per node) — and violates R1, because quota is not enforced.
- **Fail-closed** (reject all requests when the store is unreachable): preserves the
  quota guarantee but introduces an undocumented operational behavior that engineering has
  not agreed to and that R4's auditability requirement does not address.

The tension is between **R5 (distributed correctness)** and **the absence of any stated
degraded-mode policy**. Whichever choice is made must be documented explicitly — R4
requires that counting semantics be explainable, and "the store was down" is a counting
semantics answer that needs a defined outcome.

### 3(c) — `X-Customer-Id` trust boundary (R2 vs. R15)

R2 requires per-customer isolation: Customer A's traffic cannot consume Customer B's budget.
R15 states that `X-Customer-Id` is "trusted from API gateway today" — the app nodes perform
no independent verification. If the API gateway's trust assumption is correct, R2 is
satisfiable. If the `X-Customer-Id` header can be spoofed or misconfigured upstream, a
caller can present any customer ID and consume that customer's quota. The phrase "trusted
from API gateway today" implies this trust model may change, or may not hold in all
deployment slices. The rate limiter has no verification mechanism of its own; its isolation
guarantee is only as strong as the gateway's enforcement, which is outside its own trust
boundary.

### 3(d) — Clock and window definition across three nodes (R5 vs. R1 / R4)

R1 enforces RPM — requests per minute. R5 requires correctness across three nodes. No
document defines what "minute" means: fixed wall-clock bucket aligned to :00 seconds,
rolling window over the trailing 60 seconds, or something else. Across three nodes, even
small clock drift (NTP skew of tens to hundreds of milliseconds) changes the window
boundary at which a request is counted. A request arriving at 59.9 seconds on Node A may
be counted in minute N; the same request arriving at 00.1 seconds on Node B (due to drift)
may be counted in minute N+1. R4 requires that counting semantics be explainable exactly.
A distributed implementation with undefined time-source semantics cannot satisfy R4, because
the answer to "how did you count my requests" will differ depending on which node received
which request.

### 3(e) — Response-header policy attribution vs. customer-facing invisibility (R4 vs. R12)

R4 requires auditability of counting semantics. One implementation choice for auditability
is to attribute each admitted request to the policy that admitted it via a response header
(e.g., `X-Rate-Policy: burst-exception` or `X-RateLimit-Limit: 1200`). If such a header
is present on responses to Northwind during their batch window, Northwind can read their
own response headers and infer that an exception mechanism exists — directly violating R12,
which requires the exception to be invisible to the customer. The tension is between
**response-header-based policy attribution** and **customer-facing invisibility of
exceptions**. Auditability implemented purely through internal logs and config records
avoids this surface; auditability surfaced via response headers does not. This is a design
fork, not a contradiction between the requirements as written.

### 3(f) — Effective runtime limit vs. documented contracted limit for Northwind (R3 / R4 / R9 / R16 / R20)

R20 establishes that Enterprise tier is "custom — Negotiated," meaning per-customer limit
differentiation is the normal operating mode of the tier, not a deviation from it. The
"same tier, same treatment" language of R3 therefore does not impose a cross-customer
fairness constraint on Enterprise customers specifically: two Enterprise customers with
different negotiated limits are already receiving different treatment by design.

The residual tension is narrower. R16 states Northwind's documented contracted limit as
300 RPM. R9 requires that any commercial exception go through config and audit. If an
exception is implemented that raises Northwind's effective runtime limit above 300 RPM,
the auditable record (required by R4) must reflect that the effective limit diverges from
the contracted limit. Until a commercial renegotiation is complete, the config-driven
exception is admitting traffic that the current contract does not authorize. R4's
requirement to explain "exactly how we counted their requests" to an enterprise prospect
becomes complicated if the runtime policy and the signed contract state different numbers.
The tension is between **the config-driven exception mechanism (R9)** and **the requirement
to give an exact, contract-consistent account of counting semantics (R4)** — specifically
during the gap between granting a runtime exception and formalizing it in a new contract.
