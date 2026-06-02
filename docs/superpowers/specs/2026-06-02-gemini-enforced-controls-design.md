# Gemini (Antigravity/agy) Enforced Controls — Design Spec

- **Date:** 2026-06-02
- **Status:** DESIGN v2 (pre-implementation). Claude + Codex converged on the design and sequence; **v2 integrates Codex S-review findings 1-3** (HIGH: deny the live `write_file`/`replace` names not just SDK `create_file`/`edit_file`; MEDIUM: standalone hygiene script; MEDIUM: P3 probes target the live writers). **Gemini governance review** covers the §6 amendment only (it does NOT design its own enforcement, per David's directive). **David approved the plan + "lock down Gemini first"** (2026-06-02).
- **Objective:** Convert Gemini's read-only PM boundary from *guidance* (`GEMINI.md`) into an *enforced* floor at the Antigravity tool-permission layer, while sharpening Gemini's positive mandate around **Product Vision**. Gemini retains full cockpit participation and diligent read-only source verification; its only write surfaces become the **daily ledger** (via a constrained command) and **cockpit messages**.
- **Trigger:** On 2026-06-02 Gemini authored an out-of-lane live runner (`scripts/run_2025_curation.py`) and then `rm`'d it — both implementation/shell actions outside its read-only PM lane. `GEMINI.md` already prohibited exactly this. **The gap is enforcement, not instruction.**

## 1. Root cause (two open doors, both confirmed)

`agy` = **Antigravity CLI** (compiled Go binary, Gemini 3.5 Flash). Its control surface is `~/.gemini/antigravity-cli/settings.json` → `permissions`. Two independent doors were open:

1. **Native file-write tools allowed by default.** Antigravity's default policy (`confirm_run_command()`) **denies the shell tool but ALLOWS all other tools — including the file-write tools** (live: `write_file`/`replace`; SDK: `create_file`/`edit_file`) (`references/safety_policies.md` lines 12-24; `references/built_in_tools.md` lines 3-6). So Gemini could create/edit files with no prompt. This is how the runner file was written.
2. **A blanket shell allow.** `permissions.allow` contained `command(.venv/bin/python3.14)` — auto-approving **any** Python invocation (which can also write files / run arbitrary logic) with no prompt.

`GEMINI.md` (read-only PM, no shell, no code) was never the failure; the permission floor under it was permissive.

## 2. Enforcement mechanism (confirmed schema)

From the Antigravity SDK references on this machine (`~/.gemini/config/plugins/google-antigravity-sdk/references/`):

- **Policy model** (`safety_policies.md` §"Policy Resolution Order"): precedence is **Specific Deny > Specific Ask > Specific Allow > Wildcard Deny > Wildcard Ask > Wildcard Allow**, first-match-wins within a tier. A **specific `deny("tool")` cannot be overridden by any `allow`.**
- **Built-in tools** (`built_in_tools.md`): `list_directory`, `search_directory`, `find_file`, `view_file`, `finish`, `create_file`, `edit_file`, `run_command`, `ask_question`, `start_subagent`, `generate_image`.
- **CLI mapping:** the live `agy` CLI log parses `Allow:[] Deny:[] Ask:[]` (Codex-observed). So `settings.json → permissions` accepts **`allow` / `deny` / `ask`** arrays. Entries are either **tool names** or **`command(...)` predicates** for the shell tool (the existing `command(git status)` vs `command(git log)` entries confirm argument-scoped matching is supported).
- **LIVE CLI TOOL NAMES DIVERGE FROM THE SDK DOCS (critical — Codex finding 1, verified).** The SDK `built_in_tools.md` lists `create_file`/`edit_file`/`run_command`, but the **live agy environment actually exposes `write_file`, `replace`, and `run_shell_command`** as the real tool identifiers. Evidence: `~/.gemini/antigravity-cli/plugins/conductor/skills/newTrack/SKILL.md:10` explicitly permits `write_file`, `replace`, `run_shell_command`; tool-output files under `~/.gemini/tmp/dynasty-genius-product/tool-outputs/session-*/` are named `replace_replace_*` and `write_file_write_file_*`; plugin-transcript counts: `replace` ×35, `run_shell_command` ×33, `write_file` ×27. **Therefore the deny list MUST target the live names, not (only) the SDK names** — denying `create_file`/`edit_file` alone is an illusory lock because `write_file`/`replace` would stay open.

**Residual uncertainty (proven empirically in P3, §7):** that a **bare tool-name** entry in the CLI's `deny[]` array bites is documented for the SDK but not yet observed on the CLI. The negative probes confirm it before we trust it; documented fallbacks (§8) cover the failure.

## 3. The lock — `~/.gemini/antigravity-cli/settings.json` (Layer 1)

> **MACHINE config (not in repo). David applies the diff and restarts `agy`** — changes take effect only on restart.

**`permissions.deny`** (specific deny = top precedence; blocks every write/mutate/bypass surface a read-only PM does not need). **Both the LIVE-observed names and the SDK names are denied (deny both families — Codex finding 1), since a denied-but-nonexistent name is a harmless no-op but a missed live name is an open door:**

- `write_file` — **live** native file writer (primary)
- `replace` — **live** native file editor (primary)
- `create_file` — SDK name (defensive, in case agy aliases it)
- `edit_file` — SDK name (defensive)
- `generate_image` — writes image files
- `start_subagent` — **bypass vector**: a subagent could carry its own permissive tool policy and write/execute, defeating the lock. Denied because PM coordination uses the cockpit, not subagents.

The exact live-name set is re-confirmed by the P3 probe (§7); if agy exposes any additional write/mutate/delete/patch tool under another label, it is added before sign-off.

**`permissions.allow`** (tighten to the minimum Gemini legitimately needs):

- `command(.venv/bin/python3.14 scripts/tmux_msg.py)` — cockpit send
- `command(.venv/bin/python3.14 scripts/gemini_ledger_append.py)` — ledger append (§4)
- `command(git status)`, `command(git log)`, `command(git diff)`, `command(git show)` — read-only verification
- **REMOVE** `command(.venv/bin/python3.14)` and `command(.venv/bin/pytest)`.

**Deliberately NOT denied** (kept allowed for read-only source verification; these are default-allowed, not added): `view_file`, `list_directory`, `search_directory`, `find_file`, `ask_question`, `finish`.

**Deliberately NOT denied: the shell tool (`run_shell_command`, live name; `run_command` in SDK docs).** A bare `deny("run_shell_command")` would (by precedence) override the specific `command(...)` allows and break cockpit + ledger + git. Instead the shell tool is governed by the narrowed allow list; **any command not on the allow list falls back to the default `ask_user`** — so arbitrary python/shell **prompts David**, never runs silently. (P3 confirms `command(...)` predicates survive alongside the default ask, rather than being clobbered.)

**Net floor:** native writes hard-denied and un-re-grantable; subagent/image-write bypass closed; cockpit + constrained-ledger + read-only-git auto-approved; everything else prompts David; all read tools open.

## 4. Ledger-as-command — `scripts/gemini_ledger_append.py` (Layer 2; new, TDD)

Because the native write tools (`write_file`/`replace` + the SDK `create_file`/`edit_file`) are denied, Gemini cannot touch the ledger via the native editor. The **only** ledger path is this constrained command.

Contract:

- **No path argument.** The target is computed internally: `docs/agent-ledger/<today-ET>.md`. The date is derived in-process; the caller cannot redirect it.
- **Append-only.** Never truncates/rewrites; creates today's file with the standard header if absent.
- **Body from stdin or a `--body`/`--task/...` structured set**, wrapped in the canonical ledger entry header (`## HH:MM ET - Gemini (Product Manager)` + the operating-loop §"Daily Ledger Format" fields). Exact arg shape finalized in P1 TDD.
- **Fail-closed path guard:** if the resolved target ever escapes `docs/agent-ledger/` (symlink, traversal, override attempt), it raises and writes nothing.
- Importable core + thin CLI wrapper so it is unit-testable. **P1 TDD must explicitly cover: a symlinked ledger file/dir escape attempt (fails closed), and no-overwrite/no-truncate behavior (append-only verified, not just intended).**
- **Fallback (if P3 command-narrowing fails):** drop direct Gemini ledger writes entirely; Gemini drafts ledger text into the cockpit and Claude/Codex append it. Scope stays ledger + cockpit only — **no `docs/validation/` or other write grant.**

## 5. Write tripwire — `scripts/cockpit_hygiene_check.py` (Layer 3; new, TDD; defense-in-depth)

Native-write denial is unproven until P3, and the breach was an **untracked** file (a pre-commit hook would not have caught it). This is a **detection/surfacing** tool, explicitly **not** prevention.

Contract:

- Reads `git status --porcelain` **including untracked (`??`)**.
- Partitions working-tree changes into **accounted** vs **anomalous** against a configured allowlist of expected-mutable paths/globs (e.g. `docs/agent-ledger/<today>.md`, `AGENT_SYNC.md`, known untracked strategy-doc/`app/data/` patterns the cockpit already tracks).
- **Exit non-zero** when the anomalous set is non-empty; prints the offending paths.
- **Run by Claude/Codex** at session boundaries and **before accepting any Gemini source-verification CLEAR**.
- **Tension acknowledged:** it runs on the shared tree where Claude/Codex make legitimate changes, so the allowlist must be sane to avoid false positives on in-flight authored work. The allowlist mechanism is finalized in P1 TDD. It does **not** attribute authorship (git can't); it surfaces "is the tree in the expected state?" so an unexpected artifact (like the runner) is caught.
- **FORK RESOLVED (Codex technical ruling, S review):** **a new standalone `scripts/cockpit_hygiene_check.py`** — NOT an extension of `scripts/validate_governance.py`. Rationale: `validate_governance.py` is a repo/governance-invariant scanner that may later be CI/pre-commit-wired; folding a shared-working-tree untracked-file scan into it would false-positive on normal in-flight Claude/Codex work and create CI ambiguity. The hygiene check stays a **manual cockpit / session-boundary gate** with expected-mutable allowlists, isolated from CI.

## 6. Charter — positive Product Vision mandate (Layer 4; docs)

The controls are a **sharpening, not a demotion.** The docs gain David's positive mandate. Surfaces:

- **`GEMINI.md`** (repo): add the Product Vision mandate + explicit hard-stop tripwire lines ("if you are about to write or edit any file, or run a non-allowlisted command — STOP; that is Claude/Codex's lane"); keep the existing read-only/no-code prohibitions.
- **`docs/governance/02-agent-operating-loop.md`** (repo; **governance amendment** → Gemini governance review + David approval): a Gemini *enforced-scope* subsection under Agent Roles recording that the read-only PM boundary is now tool-permission-enforced (deny `write_file`/`replace`/`create_file`/`edit_file`/`generate_image`/`start_subagent`; writes = ledger-command + cockpit), so the doctrine matches the floor.
- **`dynasty-genius-pm` skill** (`~/.gemini/extensions/dynasty-genius/skills/dynasty-genius-pm/SKILL.md`; **MACHINE**, David-applied): align with the same mandate.

**The mandate (David's words, to be expanded with Gemini's own charter-bullet input in P2):** Gemini owns **Product Vision** — *what an expert dynasty fantasy manager needs at his fingertips to win his Superflex PPR league.* It reasons through four lenses simultaneously: **NFL scout, data scientist, UI/UX designer, advanced-statistics analyst.** Its standing job is to **keep the team anchored to the end goal so we build with purpose, not get lost in code** — every spec/plan/review tied back to a concrete dynasty decision (constitution §"serve a concrete dynasty decision"). It **verifies diligently, at the source, read-only.** It proposes; David approves; Claude/Codex implement.

## 7. Empirical verification (P3 — David's hands, after settings applied + `agy` restart)

Negative + positive probes, recorded in the ledger:

1. Gemini attempts arbitrary python (`.venv/bin/python3.14 -c "..."`) → **must prompt (`ask_user`) or deny**, not auto-run.
2. Gemini attempts the **actual live native write tools** on a **disposable repo temp file** — i.e. `write_file` (create/overwrite) AND `replace` (edit), by whatever labels agy presents — → **both must be DENIED** (proves the Layer-1 native-write lock against the real writers, not just the SDK names). This is the probe that closes finding 1.
3. Gemini runs `scripts/tmux_msg.py` → **allowed** (cockpit intact).
4. Gemini runs `scripts/gemini_ledger_append.py` → **allowed**, and only appends to today's ledger.
5. Gemini runs `git status` → **allowed** (verification intact).

If (2) still succeeds (bare tool-name deny does not bite on the CLI): apply §8 fallbacks.

## 8. Failure modes + fallbacks

- **F1 — broad `command(python3.14)`/`pytest` re-added** → re-opens the shell door. Guard: governance note (§6), hygiene tripwire (§5), David owns `settings.json`.
- **F2 — bare tool-name `deny[]` does not bite on the CLI** (linchpin) → native writes still possible. Fallback: remove the repo from `trustedWorkspaces` (forces a prompt on every edit) **and/or** lean on the hygiene tripwire until exact CLI deny syntax is found; keep `GEMINI.md` hard-stops. Verified by P3 probe (2).
- **F3 — ledger script taking a path arg** → directory escape. Guard: no path arg; internal date/path; append-only; fail-closed traversal guard (§4).
- **F4 — Gemini edits `settings.json` to re-grant** → if writes are denied it cannot; `~/.gemini` is outside repo-hygiene scope, so settings integrity is **David-owned** (optionally `chmod` it read-only — David's call).
- **F5 — settings change needs `agy` restart** → David restarts (§3).
- **F6 — `start_subagent` bypass** → closed by denying it (§3); re-confirm no other delegation/exec tool exists if Antigravity adds tools later.
- **F7 — deny enumeration incomplete (live vs SDK name drift)** → the live agy toolset (`write_file`/`replace`/`run_shell_command`) differs from the SDK docs; a future agy update could add a new write/patch/delete tool under another label, silently re-opening writes. Guard: deny both name families now (§3); the P3 probe attempts the **actual** native writers; treat any new agy tool as deny-by-default pending review; the hygiene tripwire (§5) catches a write that slips through.

## 9. Files changed (repo vs machine; David-gated marked)

| File | Layer | Repo/Machine | Gate |
| --- | --- | --- | --- |
| `~/.gemini/antigravity-cli/settings.json` | 1 | **Machine** | **David applies + `agy` restart (P3)** |
| `scripts/gemini_ledger_append.py` (new) | 2 | Repo | Cockpit TDD (P1); commit local |
| `scripts/cockpit_hygiene_check.py` (new) | 3 | Repo | Cockpit TDD (P1); commit local |
| `GEMINI.md` | 4 | Repo | Cockpit review (P2); commit local |
| `docs/governance/02-agent-operating-loop.md` | 4 | Repo | **Governance amendment** → Gemini governance review + David approval (P2) |
| `dynasty-genius-pm` SKILL.md | 4 | **Machine** | David applies (P2) |

## 10. Scope / non-goals

- **In scope:** the four layers above; Gemini retains cockpit (send/receive/read), read-only source verification, ledger-via-command.
- **Out of scope / non-goals:** granting Gemini any `docs/validation/` or other repo write; changing Codex/Claude permissions; any market-leakage or model/contract change; pushing to origin (binding no-push holds). This spec does **not** itself run the live S3/CFBD curation — that work is **paused** per David until the lock-down lands.

## 11. Sequence (each gated; NO push until David's word)

- **S** — this spec → cockpit dual-CLEAR (Codex technical; Gemini governance on §6/the amendment).
- **P1** — `gemini_ledger_append.py` + `cockpit_hygiene_check.py` via TDD (Codex RED → Claude GREEN) → dual CLEAR → commit LOCAL.
- **P2** — `GEMINI.md` + operating-loop enforced-scope subsection + `dynasty-genius-pm` skill (+ Gemini's charter bullets) → Gemini governance review → commit LOCAL (skill = David-applied).
- **P3** — David applies `settings.json` + restarts `agy` → run §7 probes → record results → apply §8 fallbacks if needed.
- **Postflight** — ledger + `AGENT_SYNC`; hygiene check becomes a standing pre-CLEAR gate for Gemini source-verification.
