# 02 Amendment — Cockpit Closeout Motion

- Status: DRAFT. Cockpit review → David ratification. Amends `docs/governance/02-agent-operating-loop.md`.
- Author: Claude Code (Impl / Spokesperson) · 2026-07-14
- Source directive: David, 2026-07-14 (standing order to the crew): a cockpit CLOSEOUT motion exists; codify it in the operating loop through the normal amendment process.
- Composes with: the in-flight spokesperson + Morning Brief 02 amendment (same 02 version-bump cycle; both add operating-loop sections). Land under one 02 version bump if ratified together.

## The rule David set (verbatim intent)

A cockpit **closeout motion** exists. When **Tower** announces it, each agent:
1. **Finishes the current thought to a clean stopping point — never abandons a change mid-flight.**
2. **Writes its postflight ledger entry and sync-state updates immediately** (daily `docs/agent-ledger/YYYY-MM-DD.md` + `AGENT_SYNC.md` where its state changed).
3. **Flags any approved-but-uncommitted work and anything half-done, naming where it is parked** (branch / worktree / path / PR).
4. **Replies `closed` to Tower.**

Governing fact: **anything not on disk at closeout is lost — conversation memory does not survive the session.** The motion exists to force durable state before the session ends.

Roles: **Tower ushers the closeout and verifies** each agent's on-disk state; **the spokesperson (Claude) confirms crew completion to Tower** once all lanes report `closed`.

## Proposed 02 section (new subsection under the operating loop / session-lifecycle rules)

> ### Cockpit Closeout Motion
>
> A closeout is the disciplined end-of-session flush. It is **announced by Tower** (never self-declared by a lane). On announcement, every non-Tower agent, in order:
>
> 1. **Reaches a clean stopping point.** Finish the thought or step in progress to a coherent, on-disk state. Never abandon an edit, commit, or test run mid-change — a half-applied change is worse than a parked one. If a step cannot reach a clean point quickly, park it explicitly (next item) rather than rush it.
> 2. **Writes postflight immediately.** Append the session's ledger entry (`docs/agent-ledger/YYYY-MM-DD.md`) and update `AGENT_SYNC.md` for any state the agent changed. This is not deferred to "after the reply" — it is the reply's precondition. `AGENT_SYNC.md` updates follow the serialization protocol below.
> 3. **Flags parked and uncommitted work with its location.** Every approved-but-uncommitted change, half-done build, or open review must be named with **where it is parked** — branch, worktree path, PR number, artifact path — so the next session can resume it from disk alone. "Parked at `<path>` on branch `<branch>`, N/M tests green, awaiting `<gate>`" is the shape.
> 4. **Replies with an explicit closeout status to Tower** (never a bare "done"):
>     - **`closed — clean`**: reached a clean stop, postflight + sync on disk, no uncommitted or half-done work outstanding.
>     - **`closed — parked`**: postflight + sync on disk, but named work is deliberately parked — the reply carries its **location, active command/test state, and next gate** (e.g. "parked at `<worktree>` on `<branch>`, 10/10 tests green, awaiting Codex audit CLEAR + David push").
>     - **`closeout-blocked`**: cannot reach a clean or cleanly-parked state (e.g. a mid-flight change that will not settle) — the reply says exactly what is unsettled and where, so Tower never mistakes it for a clean close.
>   A lane is not closed until its ledger + sync writes are on disk and its status reply is **delivery-verified** (cockpit-messaging skill) — a stranded `closed` is not a close.
>
> **Durability is the whole point:** conversation memory does not survive the session; anything not written to disk at closeout is lost. A truthful `parked`/`blocked` status is itself durable state — a false `clean` is the failure mode the status vocabulary exists to prevent.
>
> #### `AGENT_SYNC.md` serialization
>
> `AGENT_SYNC.md` is shared and lanes close concurrently, so a naive read-modify-write can lose a peer's update — defeating the durability the motion exists to protect. Each lane, when patching `AGENT_SYNC.md` at closeout:
> 1. **Re-reads the file immediately before writing** (never patches from a stale in-memory copy).
> 2. **Applies a conflict-preserving update** — append/merge its own lane's state without overwriting another lane's section.
> 3. **Defers to Tower sequencing/retry** if a concurrent write intervenes between its re-read and its write: Tower orders the writes and the lane retries against the fresh file rather than clobbering.
>
> #### Roles
>
> - **Non-Tower lanes** flush, park with location, and reply a closeout status (above).
> - **Spokesperson** consolidates the lanes' statuses and **confirms crew completion to Tower with a faithful report** — it does not authorize the close, and it surfaces every non-clean lane exactly as reported (no smoothing a `parked`/`blocked` lane into a tidy close).
> - **Tower** ushers and verifies: it announces the motion, confirms each lane's on-disk state, and **performs its own closeout last** — Tower cannot reply `closed` to itself, so its terminal condition is: after the spokesperson's faithful crew report, Tower flushes **its own** ledger/sync state, verifies the durable record, and only then closes the cockpit. Tower closing is the session's terminal act.

## Guardrails / falsification seeds

1. **Closeout is not a commit authorization.** Flushing ledger + sync state is verifier-exempt state-doc maintenance; committing/pushing code still needs cockpit CLEAR + David's word. Closeout **parks** uncommitted work with its location — it does not license landing it to beat the deadline.
2. **"Clean stopping point" is not "rush to finish."** The motion must not pressure a lane into a hasty commit of unreviewed work. When in doubt, park explicitly — a clearly-located parked item is a successful closeout, an abandoned mid-edit is a failed one.
3. **Tower announces; lanes do not self-close.** A lane replying `closed` without a Tower announcement is out of protocol (mirrors: repo-state declarations are Tower/Codex's, not self-granted).
4. **Spokesperson confirms, does not suppress.** The crew-completion confirmation to Tower reports every lane's status faithfully, including any lane that is NOT clean — it never smooths over an unflushed lane to report a tidy close.
5. **Delivery verification applies to the `closed` reply.** Per the cockpit-messaging skill, a `closed` reply is not delivered until sender-verified — a stranded `closed` is not a close.

## Scope

Docs/governance only (02 operating loop + this spec). No code. Adds a session-lifecycle subsection; changes no existing rule. Land under the same 02 version bump as the spokesperson + Morning Brief amendment if both ratify together.
