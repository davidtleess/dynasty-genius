# Zero-anchor ticket-boundary rerun — raw sealed outputs

**Date:** 2026-07-25
**Status:** Raw evidence. No prior candidate or Tower framing was supplied.

## Method

Three fresh subagents were started with `fork_turns="none"`. They were instructed not to inspect the filesystem, repository, internet, or any prior artifact. They received only David's verbatim ticket standard and the same neutral task. They were explicitly barred from using prior candidate labels or the word introduced by Tower.

The first-pass answers below were received and sealed before any real clause was shown. The second pass then asked each reviewer to apply only its already-stated rule to the same ten anonymized clauses, without revising the rule or proposing replacement wording.

These are three isolated model runs, not three human reviewers; shared model priors remain a source of dependence.

## Common first-pass prompt

> You are a context-free independent analyst. Do not inspect any filesystem, repository, internet source, or prior artifact. Reason ONLY from the standard quoted below. You have not been told any candidate answers, disputed examples, prior reviews, or desired outcome.
>
> STANDARD (verbatim): "Software development tickets should define the problem clearly while leaving room for the developer to find the best solution. A good ticket balances necessary context with creative freedom by focusing on the what and the why rather than the exact how." Include: clear problem statement, acceptance criteria that say when the work is done, context and data, constraints. Leave to the developer: technical design, implementation steps, library and tool choice, problem-solving and how to test a fix.
>
> TASK: Derive from first principles a practical boundary between a legitimate ticket constraint and an impermissible prescription of implementation. Provide: (1) one sentence a project owner could ratify verbatim; (2) an operational decision procedure a stranger can apply without asking the author; (3) 4 examples you invent yourself, two on each side; (4) the strongest failure mode or ambiguity in your own rule; (5) whether the standard itself is sufficient or needs an additional owner decision. Do not use the terms Candidate A/B/C/D or [Tower's term]. Do not speculate about any particular repository. Return your analysis directly; do not write files.

## First pass — reviewer 1, verbatim

### 1. Ratifiable sentence

“A ticket may constrain an externally observable outcome or an independently established boundary—such as law, contract, compatibility, safety, budget, or platform policy—but it must not mandate an internal mechanism, sequence, tool, or test method unless that mandate is itself a ratified boundary and the ticket states the consequence it protects against.”

### 2. Operational decision procedure

Apply this to each directive in the ticket:

1. **Atomize it.** Separate mixed statements into individual requirements.
2. **Boundary test:** Can compliance be judged from system behavior, delivered data, or another externally visible result without inspecting the implementation? If yes, it is an outcome constraint.
3. **Independent-boundary test:** If it concerns internals, does the ticket identify a pre-existing law, contract, published interface, security policy, supported platform, budget, or other ratified boundary—and explain the harm from violating it? If yes, it may be a legitimate constraint.
4. **Equivalent-solution test:** Could a materially different design satisfy every outcome and established boundary? If yes, rejecting it merely because it uses different code structure, tools, sequencing, or testing would be an implementation prescription.
5. **Testing test:** Acceptance criteria may specify behavior or evidence that must be demonstrated, but not the test framework, test layer, or procedure used to demonstrate it.
6. **Default rule:** When an internal directive lacks a cited boundary and independent rationale, treat it as a nonbinding suggestion or remove it. If one sentence contains both an outcome and a mechanism, retain the outcome and separate or discard the mechanism.

### 3. Examples

Legitimate constraints:

- “Uploads of PNG and JPEG files up to 10 MB must complete within two seconds at the 95th percentile, because the published mobile-flow service level requires it.”
- “The release must remain compatible with the existing v3 webhook contract and must not interrupt event delivery, because external partners cannot migrate in the current release window.”

Implementation prescriptions:

- “Create an `UploadQueueManager` class, store its state in Redux, and divide the change among three specified modules.”
- “Fix failed requests with exponential backoff and three retries, then prove the fix with Cypress end-to-end tests.”

### 4. Strongest failure mode

The hardest ambiguity is that some internal-looking requirements—approved technologies, architectural boundaries, cryptographic controls, or deployment patterns—may represent genuine organization-wide constraints. An author can also disguise a personal preference as such a constraint. A stranger cannot reliably distinguish the two unless the ticket identifies an authoritative source and the independent risk or obligation involved.

### 5. Is the standard sufficient?

The standard gives the right principle but is not sufficient for consistent adjudication. The owner should additionally ratify what qualifies as an “independently established boundary,” what evidence must be cited, and the default treatment of unsupported internal directives. The sentence and procedure above supply that missing decision.

## First pass — reviewer 2, verbatim

### 1. Ratifiable sentence

“A ticket may require observable outcomes and explicitly identified, pre-existing non-negotiable boundaries, but it must not select internal design, implementation steps, dependencies, tools, or testing methods merely because the author prefers them.”

### 2. Operational decision procedure

Apply this to each requirement independently:

1. Identify what would violate the requirement.
2. Ask whether the violation can be described without inspecting the implementation—for example, incorrect behavior, broken compatibility, unacceptable performance, mishandled data, or breach of a documented policy.
   - If yes, it is probably a legitimate constraint.
3. If the requirement names an architecture, algorithm, component, library, tool, sequence of work, or testing technique, apply a provenance test:
   - Does the ticket explicitly identify it as a pre-existing external contract or owner-ratified boundary and explain why it is non-negotiable?
   - If yes, treat it as an inherited constraint.
   - If no, treat it as an implementation prescription.
4. Apply a substitution test: could a developer replace the proposed technical means while preserving every required outcome and documented boundary?
   - If yes, the ticket must permit that substitution.
   - If no, the ticket must state the independent constraint that makes substitution impossible.
5. When the rationale or provenance is missing, classify the clause as unresolved—not as a legitimate constraint—until the ticket is rewritten.

### 3. Examples

Legitimate constraints:

- “Existing clients must continue to receive the documented version-1 response fields for six months after release, because they cannot all migrate simultaneously.”
- “Customer tax identifiers must never be sent to the analytics provider, and records must be deleted within 30 days of account closure.”

Impermissible implementation prescriptions:

- “Use Redis and the Redlock algorithm to prevent duplicate processing.”
- “Add a React debounce hook, mock timers in Jest, and implement the change in three sequential commits.”

### 4. Strongest failure mode

The boundary between “outcome” and “means” is not always intrinsic to the wording. A technical choice may be a genuine compatibility or governance boundary, while an apparently outcome-based requirement may be so narrowly specified that it effectively dictates one implementation. The rule therefore depends on explicit provenance: without a documented reason showing that a technical restriction predates the ticket author’s proposed solution, a stranger cannot reliably distinguish necessity from preference.

### 5. Sufficiency of the standard

The standard gives the correct governing principle but is not operationally sufficient for edge cases. It needs an additional owner decision defining which pre-existing technical boundaries are genuinely non-negotiable, where they are recorded, and what evidence a ticket must provide when incorporating one.

## First pass — reviewer 3, verbatim

### 1. Ratifiable sentence

“A ticket may constrain implementation only when the constraint is itself a non-negotiable, owner-ratified boundary—such as compatibility, security, legal, operational, or established architecture—and states both its reason and observable condition; otherwise, the ticket must specify the required outcome while leaving design, tools, implementation steps, problem-solving, and test method to the developer.”

### 2. Operational decision procedure

For each mandatory clause:

1. Apply the substitution test: could a materially different implementation produce the same required behavior and satisfy the underlying need?
2. If yes, rejecting that alternative merely because it uses a different internal mechanism would make the clause an implementation prescription.
3. Presume a clause is prescriptive if it mandates code structure, algorithm, execution sequence, library, tool, or testing technique.
4. Override that presumption only when the ticket identifies a binding source for the exact restriction—such as a public interface, law, security policy, deployment environment, interoperability dependency, or owner-ratified architectural rule—and explains why it is necessary.
5. Express a legitimate constraint as an observable invariant or boundary and include its rationale. Put optional technical ideas in clearly nonbinding notes.
6. If the ticket supplies no binding source or necessity for an exact technical choice, classify it as impermissible prescription without asking the author.

### 3. Examples

Legitimate constraints:

- “CSV exports must retain the existing column names and ordering because a partner’s importer depends on that contract, and a 100,000-row export must complete within 30 seconds.”
- “Raw Social Security numbers must not be persisted, and all processing must remain in the approved region, as required by the governing data policy.”

Impermissible prescriptions:

- “Add Redis in the service layer, use a five-minute TTL, and invalidate each key after a database write.”
- “Mock `fetch` in a Jest unit test, then implement a 300 ms debounce with a React effect.”

### 4. Strongest failure mode

A preferred implementation can be disguised as a “constraint” by attaching a weak rationale, while broad phrases such as “established architecture” can be used to justify nearly any mandate. The rule therefore depends on knowing which policies, interfaces, and architectural decisions genuinely have owner-ratified authority; ticket wording alone cannot establish that authority reliably.

### 5. Sufficiency of the standard

The standard gives the correct direction but is not sufficient for disputed edge cases. It needs an additional owner decision establishing the burden of proof: an exact technical requirement is binding only when its necessity and authoritative source are stated; otherwise it is nonbinding guidance and the developer retains the choice.

## Common second-pass prompt

> Your first-pass rule is now sealed. Do not revise it and do not inspect any external source. Apply ONLY your already-stated rule to the ten anonymized clauses below. For each return exactly: LEGITIMATE CONSTRAINT / IMPERMISSIBLE PRESCRIPTION / DEPENDS ON MISSING AUTHORITY, plus one sentence why. Distinguish an engineering acceptance criterion from an organization-wide process gate when relevant. Do not propose replacement wording.

The clauses appear beside the classifications below.

## Second pass — classification matrix

| # | Anonymized clause | Reviewer 1 | Reviewer 2 | Reviewer 3 |
|---|---|---|---|---|
| 1 | “Pin library X.” | **IMPERMISSIBLE** — mandates a library choice without a ratified boundary | **IMPERMISSIBLE** — selects a dependency rather than an outcome/inherited boundary | **IMPERMISSIBLE** — specific tool with no binding source |
| 2 | “A degenerate input produces a named unavailable state, and the promotion gate refuses on that state.” | **LEGITIMATE** — observable fail-closed behavior | **LEGITIMATE** — externally verifiable degenerate-input and gate behavior | **LEGITIMATE** — observable failure-state and promotion behavior |
| 3 | “The change fails a contract test before implementation.” | **IMPERMISSIBLE** — testing method and sequence, absent process mandate | **DEPENDS** — valid only if owner-ratified organization-wide process gate | **IMPERMISSIBLE** — testing technique and sequence |
| 4 | “The quantity is computed in exactly one module.” | **IMPERMISSIBLE** — internal code structure | **IMPERMISSIBLE** — internal module topology | **IMPERMISSIBLE** — internal organization |
| 5 | “The result is reproduced by a second review lane.” | **DEPENDS** — process gate needs ratified policy | **DEPENDS** — organization-wide review gate needs authority | **DEPENDS** — owner-ratified process gate needed |
| 6 | “The result is reproducible from a pinned random seed.” | **LEGITIMATE** — fixed input state is observable | **LEGITIMATE** — fixed-input reproducibility is measurable | **IMPERMISSIBLE** — particular mechanism absent authoritative protocol |
| 7 | “Calibration error is reported by decile.” | **LEGITIMATE** — observable reporting output | **LEGITIMATE** — analytical output/grouping, implementation open | **LEGITIMATE** — observable reporting output |
| 8 | “No ceiling artifact may reach any downstream consumer.” | **LEGITIMATE** — downstream safety invariant | **LEGITIMATE** — downstream data-integrity boundary | **LEGITIMATE** — downstream safety invariant |
| 9 | “A new irreplaceable store is added to the named backup manifest in the same change set.” | **DEPENDS** — organization-wide release gate needs authority | **DEPENDS** — named manifest and timing need authority | **LEGITIMATE** — identified operational-protection boundary |
| 10 | “An unjoinable row goes to triage and is never silently dropped.” | **LEGITIMATE** — observable data-loss/handling behavior | **LEGITIMATE** — observable handling and loss prevention | **LEGITIMATE** — observable data-integrity behavior |

## Raw second-pass nuances

- Clause 3: no reviewer accepted it unconditionally. Two called it impermissible as written; one required an owner-ratified process mandate.
- Clause 5: all three required missing authority and distinguished a review-process gate from an engineering acceptance criterion.
- Clause 6: the only direct conceptual split. Two read “from a pinned seed” as a measurable fixed-input condition; one read it as a particular mechanism.
- Clause 9: two required proof of authority for the exact manifest and same-change rule; one treated the stated operational boundary as enough. Revealing a pre-existing manifest law would settle the missing-authority branch without changing the reviewers' rules.
