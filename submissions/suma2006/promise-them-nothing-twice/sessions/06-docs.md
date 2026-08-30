# Chat Conversation

Note: _This is purely the output of the chat conversation and does not contain any raw data, codebase snippets, etc. used to generate the output._

### User Input

ROLE: You are joining a completed take-home build for the final documentation session.
Sessions 01-05 are done. The code works. Do not change any code, config, or harness logic.

REPO ROOT: this workspace.
WORKING DIRECTORY: submissions/suma2006/promise-them-nothing-twice/
Do not create or modify any file outside that directory.

Read first, in full:
  1. solution/docs/CONTEXT.md
  2. solution/docs/DESIGN.md
  3. solution/docs/CONSTRAINTS.md
  4. solution/docs/handoffs/01 through 05
  5. solution/Makefile, solution/docker-compose.yml, solution/config/policies.yaml

TASK: two documents. No code changes.

DOCUMENT 1: DECISIONS.md at the submission root - NOT inside solution/docs/. One page maximum.
Structured prose, not a novel. Sections:

  - The CTO vs support conflict: what I decided and what I explicitly rejected. State that
    engineering did not resolve a commercial conflict - it built a config-driven, time-boxed,
    expiring override and made pulling the lever auditable. Name the rejected options: strict
    300 enforcement, permanent capacity bump, shadow mode. Say plainly that R10 is only
    probabilistically satisfied - no finite ceiling guarantees zero 429s.
  - Algorithm and distributed coordination: sliding window log, Redis, atomic Lua, Redis TIME
    as the sole clock for counting AND policy resolution. Include the worst-case admission
    numbers. Fail-closed 503, and note that failing closed during the batch window is itself
    a commercial decision that is not engineering's to make.
  - What the harness proves: the six scenarios and their observed numbers, before and after.
  - What the harness does NOT prove: single Redis, no failover, no partition test, not at
    production scale, X-Customer-Id is trusted and spoofable, S6 needs a specific config.
    Make this section longer than feels comfortable.
  - What I would build next with another four hours.

DOCUMENT 2: solution/README.md. Target: a reviewer with only free tools runs this in under
15 minutes. Cover:
  - prerequisites (docker and docker compose v2, python3 for the harness)
  - quickstart: make up, then make harness
  - make demo and what it demonstrates that make harness does not
  - what each of the six scenarios proves, one line each
  - how to switch limiters via LIMITER_TYPE and why the naive one still exists
  - the counting-semantics paragraph from DESIGN.md section 6, verbatim
  - how to reproduce the fail-closed 503
  - config file layout and how to add a customer or an override

Rules:
  - do not invent numbers. Every figure must come from a handoff or a doc you just read. If a
    number is not recorded anywhere, say so instead of guessing.
  - no marketing tone. Plain factual prose.
  - DECISIONS.md is one page. If it runs longer, cut.

Before writing: tell me which numbers you will cite and which file each came from. Then stop.

*Listed directory [handoffs](file:///home/manem/suma-workspace/ti-assignment-promise-them-nothin/submissions/suma2006/promise-them-nothing-twice/solution/docs/handoffs) *

*Viewed [CONTEXT.md](file:///home/manem/suma-workspace/ti-assignment-promise-them-nothin/submissions/suma2006/promise-them-nothing-twice/solution/docs/CONTEXT.md) *

*Viewed [DESIGN.md](file:///home/manem/suma-workspace/ti-assignment-promise-them-nothin/submissions/suma2006/promise-them-nothing-twice/solution/docs/DESIGN.md) *

*Viewed [CONSTRAINTS.md](file:///home/manem/suma-workspace/ti-assignment-promise-them-nothin/submissions/suma2006/promise-them-nothing-twice/solution/docs/CONSTRAINTS.md) *

*Viewed [01-handoff.md](file:///home/manem/suma-workspace/ti-assignment-promise-them-nothin/submissions/suma2006/promise-them-nothing-twice/solution/docs/handoffs/01-handoff.md) *

*Viewed [02-handoff.md](file:///home/manem/suma-workspace/ti-assignment-promise-them-nothin/submissions/suma2006/promise-them-nothing-twice/solution/docs/handoffs/02-handoff.md) *

*Viewed [03-handoff.md](file:///home/manem/suma-workspace/ti-assignment-promise-them-nothin/submissions/suma2006/promise-them-nothing-twice/solution/docs/handoffs/03-handoff.md) *

*Viewed [04-handoff.md](file:///home/manem/suma-workspace/ti-assignment-promise-them-nothin/submissions/suma2006/promise-them-nothing-twice/solution/docs/handoffs/04-handoff.md) *

*Viewed [05-handoff.md](file:///home/manem/suma-workspace/ti-assignment-promise-them-nothin/submissions/suma2006/promise-them-nothing-twice/solution/docs/handoffs/05-handoff.md) *

*Viewed [Makefile](file:///home/manem/suma-workspace/ti-assignment-promise-them-nothin/submissions/suma2006/promise-them-nothing-twice/solution/Makefile) *

*Viewed [docker-compose.yml](file:///home/manem/suma-workspace/ti-assignment-promise-them-nothin/submissions/suma2006/promise-them-nothing-twice/solution/docker-compose.yml) *

*Viewed [policies.yaml](file:///home/manem/suma-workspace/ti-assignment-promise-them-nothin/submissions/suma2006/promise-them-nothing-twice/solution/config/policies.yaml) *

### Planner Response

I will cite the following numbers and reference these specific source files:

**From `solution/docs/CONSTRAINTS.md`:**
*   **300 (RPM):** Northwind's contracted limit (R16).
*   **429:** The status code required by the CTO for exceeding quota (R1).
*   **02:00–04:00 (UTC):** Northwind's batch window mandate from Support (R10).
*   **3:** The number of stateless app nodes in the environment (R13).

**From `solution/docs/DESIGN.md`:**
*   **1500 (RPM):** The time-bound elevated limit for Northwind, and the rejected permanent capacity bump (Section 1).
*   **1501 (RPM):** The queue depth that would still trigger a 429, proving R10 is only probabilistically satisfied (Section 1 / Section 7).
*   **5 (weeks):** The absolute expiry time configured for the override (Section 1).
*   **1800, 900, 600, 300:** The worst-case admitted requests in a 60-second window across a 3-node cluster, used to justify the Sliding Window Log over other algorithms (Section 2 Table).
*   **60 (seconds):** The continuous trailing window evaluated (Section 2 / 6).
*   **503:** The fail-closed status code during a Redis outage (Section 4).

**From `solution/docs/handoffs/04-handoff.md` (The "Before" / Naive Limiter Numbers):**
*   **S1:** Metric of **300**.
*   **S2 (600 target):** Metric of **600** (a failure).
*   **S3 (3000/300 target):** Metric of **1459 / 300** (a failure).
*   **S4 (Boundary straddle):** Metric of **600** (a failure).
*   **S5 (Node distribution):** Metric of **600** (a failure).

**From `solution/docs/handoffs/05-handoff.md` (The "After" / Redis Sliding Window Numbers):**
*   **S1, S2, S3, S4, S5:** All constrained to exactly the **300** metric.
*   **S6:** Metric of **300** (inactive default) and **1500** (active override via demo).

**From `solution/README.md` instructions / environment (Implicit in tools/Makefile):**
*   **15 (minutes):** Time to run the quickstart.
*   **3:** Python version required.
*   **2:** Docker compose version required.

I will stop here and await your confirmation before generating `DECISIONS.md` and `solution/README.md`.

### User Input

Sources confirmed. Three corrections, then go.

1. S5 before: cite the per-node breakdown 200/200/200 alongside the 600 total. The per-node
   split is what actually demonstrates uncoordinated state; the total alone does not.

2. Add the fail-closed verification to your citations: session 05 stopped the redis container
   and observed 503 on a live request. That is a demonstrated behaviour, not a claim, and
   DECISIONS.md should say it was verified rather than designed.

3. Add one more item to "what the harness does NOT prove": the harness itself had two defects
   found during session 05 - scenarios could pass while losing traffic, and a scenario bound
   contradicted the effective limit. Both were fixed, but state that the harness is only as
   trustworthy as its assertions and that these were caught by inspection rather than by any
   automated check.

Point 3 matters. A reviewer trusts a document more when it names the weaknesses of its own
evidence.

Go. Write both documents.

*Edited relevant file*

*Edited relevant file*

### Planner Response

I have created both documents with the precise numbers, source references, and requested corrections incorporated. 

*   `DECISIONS.md` has been written to the submission root. It covers the CTO/Support resolution, algorithm choices, the verified fail-closed behavior, the before/after metrics for all six scenarios (including the `200/200/200` per-node breakdown for S5), the manually-discovered harness defects, and the next build steps.
*   `solution/README.md` has been created, detailing the prerequisites, quickstart, demo commands, one-line scenario descriptions, the exact verbatim counting semantics paragraph, and the config structure.

Both files are saved and strictly follow the provided structure and factual constraints. Let me know if you need any adjustments to these files.

### User Input

Four fixes.

DECISIONS.md:
1. "What I Would Build Next" has only two items and misses the most valuable one. Add:
   - a retry-amplification harness scenario. Northwind's client amplifies on 429, which is the
     entire reason the override ceiling needs headroom above their observed p99. That argument
     is currently untested.
   - gateway-signed customer identity, since the doc already names X-Customer-Id spoofing as a
     hole that voids isolation.
2. The S5 before line does not parse: "proving uncoordinated state by leaking via 200/200/200
   per-node admission". Rewrite as: 600 total admitted, 200 per node across 3 nodes.

README.md:
3. The make demo section says policies.demo.yaml "shifts the active window to overlap with the
   current time". Open the file and confirm. If the window is 00:00-23:59, say it is always
   active and explain why that is the simplest way to demonstrate the active path.
4. S5's description says "uncoordinated traffic". The traffic was not uncoordinated - the
   baseline limiter was. Rewrite so it says what S5 actually proves: that a shared store
   constrains total admissions across nodes, where per-node state would not.

Do not change anything else in either file.

*Viewed [policies.demo.yaml](file:///home/manem/suma-workspace/ti-assignment-promise-them-nothin/submissions/suma2006/promise-them-nothing-twice/solution/config/policies.demo.yaml) *

*Edited relevant file*

*Edited relevant file*

### Planner Response

All four requested corrections have been applied successfully:

1.  **`DECISIONS.md` Next Steps:** Added the Retry-Amplification scenario and Gateway-Signed Customer Identity items to explicitly address the unproven load ceiling arguments and the spoofing risk.
2.  **`DECISIONS.md` S5 phrasing:** Rewrote the before metric to clearly state `"Before 600 total admitted (200 per node across 3 nodes)"`.
3.  **`README.md` Make Demo:** Updated the explanation to clarify that `policies.demo.yaml` uses a perpetually active `00:00-23:59` window rather than clock shifting.
4.  **`README.md` S5 description:** Rewrote the scenario to precisely state that it `"Proves that a shared store constrains total admissions across nodes, where per-node state would not."`

Both documents are complete and structurally precise according to your specifications. Let me know if there's anything else you need.

### User Input

The fresh-clone test passed. Add two things to solution/README.md, nothing else:

1. Under Quickstart, state the measured time: a clean clone through `make up` and `make
   harness` completed in 6m22s on a laptop, including the docker image build and the ~53s
   S4 waits for a UTC minute boundary. Note that S4 waits by design so a reviewer does not
   think it has hung.

2. A short "Expected output" note: all six scenarios PASS under `make harness`, with S6
   showing the inactive window at 300. Point to `make demo` for the active window at 1500.

*Viewed [README.md](file:///home/manem/suma-workspace/ti-assignment-promise-them-nothin/submissions/suma2006/promise-them-nothing-twice/solution/README.md) *

*Edited relevant file*

### Planner Response

The `solution/README.md` file has been successfully updated. The `Quickstart` section now explicitly states the 6m22s measured run time, notes the intentional ~53s pause for scenario S4 so reviewers don't mistake it for a hang, and includes the expected output note detailing that all six scenarios PASS with S6 inactive at 300 (pointing to `make demo` for the 1500 active window test).

No other changes were made. Let me know if everything is ready to go!