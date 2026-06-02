# Gemini (Antigravity/agy) Enforced Controls — Design Spec

- **Date:** 2026-06-02
- **Status:** DESIGN v2 (pre-implementation). Claude + Codex converged on the design and sequence; **v2 integrates Codex S-review findings 1-3** (HIGH: deny the live `write_file`/`replace` names not just SDK `create_file`/`edit_file`; MEDIUM: standalone hygiene script; MEDIUM: P3 probes target the live writers). **Gemini governance review** covers the §6 amendment only (it does NOT design its own enforcement, per David's directive). **David approved the plan + "lock down Gemini first"** (2026-06-02). **UPDATE — see §12 (P3 amendment):** S/P1/P2 built + committed LOCAL (`fea3bf9`, `1075c2b`, `2c9d370`); P3 empirically proved the Layer-1 native-write *deny* is **UNACHIEVABLE on the agy CLI** → David ruled **finalized posture A** (shell-lock + mandatory hygiene tripwire + charter; native writes are **detected, not prevented**).
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

**`permissions.deny` — ATTEMPTED, NOT EFFECTIVE (P3, §12).** The design intent was a specific-deny on every write/mutate/bypass surface (`write_file`/`replace` live + `create_file`/`edit_file` SDK aliases + `generate_image` + `start_subagent`). **P3 proved this does not work:** the agy CLI did not retain the `deny[]` entries across `settings.json` persistence, and even when an agy log parsed them, native write calls were not enforced — native `write_file`/`replace` succeeded. The agy CLI `settings.json permissions` block governs **only `command(...)` (shell) entries**, not native tools. This bullet list is retained as the recorded attempt; **it is NOT the enforcement.** Native-write enforcement is the §5 tripwire (detection) + the §6 charter (mandate). See §12.

**`permissions.allow`** (tighten to the minimum Gemini legitimately needs):

- `command(.venv/bin/python3.14 scripts/tmux_msg.py)` — cockpit send
- `command(.venv/bin/python3.14 scripts/gemini_ledger_append.py)` — ledger append (§4)
- `command(git status)`, `command(git log)`, `command(git diff)`, `command(git show)` — read-only verification
- **REMOVE** `command(.venv/bin/python3.14)` and `command(.venv/bin/pytest)`.

**Deliberately NOT denied** (kept allowed for read-only source verification; these are default-allowed, not added): `view_file`, `list_directory`, `search_directory`, `find_file`, `ask_question`, `finish`.

**Deliberately NOT denied: the shell tool (`run_shell_command`, live name; `run_command` in SDK docs).** A bare `deny("run_shell_command")` would (by precedence) override the specific `command(...)` allows and break cockpit + ledger + git. Instead the shell tool is governed by the narrowed allow list; **any command not on the allow list falls back to the default `ask_user`** — so arbitrary python/shell **prompts David**, never runs silently. (P3 confirms `command(...)` predicates survive alongside the default ask, rather than being clobbered.)

**Net floor ACHIEVED (posture A, P3-verified):** the allow-list tightening **persists and works** — cockpit + constrained-ledger + read-only-git are auto-approved; **any non-allowlisted shell/python prompts David** (the silent-script hole is closed); all read tools stay open. **Native file writes are NOT prevented** (the `deny[]` above is not honored by agy) — they are enforced by **detection** (the §5 tripwire, mandatory gate) + **mandate** (§6 charter), not prevention. See §12.

## 4. Ledger-as-command — `scripts/gemini_ledger_append.py` (Layer 2; new, TDD)

The native write tools (`write_file`/`replace`) cannot be config-denied on agy (P3, §12), so this command is the **sanctioned** ledger path (by mandate), not the only *physically possible* one — a native-editor ledger write is still possible but is out-of-lane and caught by the §5 tripwire. The command exists so the legitimate ledger write needs no native editor at all: it is path-locked (no path arg), append-only, Gemini-attributed, and fail-closed on escape.

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
- **Run by Claude/Codex** at session boundaries and **before accepting any Gemini source-verification CLEAR**. **Exact gate command:** `.venv/bin/python3.14 scripts/cockpit_hygiene_check.py` (the script is not marked executable, so invoke via the venv interpreter, not `./`), adding `--allow <glob>` for known in-flight/session-mutable files. Non-zero exit = anomalies present.
- **Tension acknowledged:** it runs on the shared tree where Claude/Codex make legitimate changes, so the allowlist must be sane to avoid false positives on in-flight authored work. The allowlist mechanism is finalized in P1 TDD. It does **not** attribute authorship (git can't); it surfaces "is the tree in the expected state?" so an unexpected artifact (like the runner) is caught.
- **FORK RESOLVED (Codex technical ruling, S review):** **a new standalone `scripts/cockpit_hygiene_check.py`** — NOT an extension of `scripts/validate_governance.py`. Rationale: `validate_governance.py` is a repo/governance-invariant scanner that may later be CI/pre-commit-wired; folding a shared-working-tree untracked-file scan into it would false-positive on normal in-flight Claude/Codex work and create CI ambiguity. The hygiene check stays a **manual cockpit / session-boundary gate** with expected-mutable allowlists, isolated from CI.

## 6. Charter — positive Product Vision mandate (Layer 4; docs)

The controls are a **sharpening, not a demotion.** The docs gain David's positive mandate. Surfaces:

- **`GEMINI.md`** (repo): add the Product Vision mandate + explicit hard-stop tripwire lines ("if you are about to write or edit any file, or run a non-allowlisted command — STOP; that is Claude/Codex's lane"); keep the existing read-only/no-code prohibitions.
- **`docs/governance/02-agent-operating-loop.md`** (repo; **governance amendment** → Gemini governance review + David approval): a Gemini *enforced-scope* note under Agent Roles recording the posture-A reality — **shell is prompt-gated** (non-allowlisted commands prompt David), **native file writes are detection-enforced** (the §5 hygiene tripwire as a mandatory gate) **+ mandate**, not config-denied (P3); sanctioned writes = the ledger command + cockpit. The mandatory-tripwire-gate rule is recorded as cockpit doctrine here.
- **`dynasty-genius-pm` skill** (`~/.gemini/extensions/dynasty-genius/skills/dynasty-genius-pm/SKILL.md`; **MACHINE**, David-applied): align with the same mandate.

**The mandate (David's words, to be expanded with Gemini's own charter-bullet input in P2):** Gemini owns **Product Vision** — *what an expert dynasty fantasy manager needs at his fingertips to win his Superflex PPR league.* It reasons through four lenses simultaneously: **NFL scout, data scientist, UI/UX designer, advanced-statistics analyst.** Its standing job is to **keep the team anchored to the end goal so we build with purpose, not get lost in code** — every spec/plan/review tied back to a concrete dynasty decision (constitution §"serve a concrete dynasty decision"). It **verifies diligently, at the source, read-only.** It proposes; David approves; Claude/Codex implement.

## 7. Empirical verification (P3 — David's hands, after settings applied + `agy` restart)

Negative + positive probes, recorded in the ledger. **[AMENDED §12: P3 was run — actual results: probe (1) PROMPTED ✅; probe (2) "both must be DENIED" was NOT met — native writes SUCCEEDED ❌ (deny stripped); probes (3)/(4)/(5) allowed ✅; tripwire flagged the probe write ✅. Posture A adopted.]**

1. Gemini attempts arbitrary python (`.venv/bin/python3.14 -c "..."`) → **must prompt (`ask_user`) or deny**, not auto-run.
2. Gemini attempts the **actual live native write tools** on a **disposable repo temp file** — i.e. `write_file` (create/overwrite) AND `replace` (edit), by whatever labels agy presents — → **both must be DENIED** (proves the Layer-1 native-write lock against the real writers, not just the SDK names). This is the probe that closes finding 1.
3. Gemini runs `scripts/tmux_msg.py` → **allowed** (cockpit intact).
4. Gemini runs `scripts/gemini_ledger_append.py` → **allowed**, and only appends to today's ledger.
5. Gemini runs `git status` → **allowed** (verification intact).

If (2) still succeeds (bare tool-name deny does not bite on the CLI): apply §8 fallbacks.

## 8. Failure modes + fallbacks

- **F1 — broad `command(python3.14)`/`pytest` re-added** → re-opens the shell door. Guard: governance note (§6), hygiene tripwire (§5), David owns `settings.json`.
- **F2 — bare tool-name `deny[]` does not bite on the CLI** (linchpin) → native writes still possible. **RESOLVED as a CONFIRMED NEGATIVE (P3, §12):** agy strips the `deny[]` block on restart AND `gitFolder.allowWrite:false` does not gate write tools — there is NO config/flag that denies native writes while preserving reads. Adopted fallback = the hygiene tripwire (§5) as a mandatory gate + `GEMINI.md` hard-stops + the shell-lock. `trustedWorkspaces`-untrust REJECTED (it governs `view_file`/`create_file`/`edit_file` together → would also block reads). The only true hard-deny is Option C (SDK `policy.deny`), not chosen.
- **F3 — ledger script taking a path arg** → directory escape. Guard: no path arg; internal date/path; append-only; fail-closed traversal guard (§4).
- **F4 — Gemini widens its own `settings.json` allow-list** → since native writes are NOT prevented (P3), Gemini *can* edit `~/.gemini` files, which are outside repo-hygiene scope so the §5 tripwire won't catch them. Mitigation: settings integrity is **David-owned** — David periodically eyeballs `settings.json`, never re-adds `command(.venv/bin/python3.14)`/`command(.venv/bin/pytest)`, and never launches agy with `--dangerously-skip-permissions`; optionally `chmod` the settings read-only (David's call).
- **F5 — settings change needs `agy` restart** → David restarts (§3).
- **F6 — `start_subagent` bypass** → the deny does not take (P3), but a spawned subagent's file writes still land in the working tree, so the §5 tripwire catches them; the §6 mandate prohibits spawning subagents.
- **F7 — new agy write tool under another label** → moot for *prevention* (no settings deny works anyway), but the §5 tripwire catches any write regardless of which tool produced it (it inspects the working tree, not the tool name). If Antigravity later ships a real settings-level tool-deny, revisit Layer-1 prevention then.

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

## 12. P3 RESULT — empirical outcome + finalized posture (2026-06-02 AMENDMENT)

P3 was executed (David applied `settings.json` + restarted `agy`; probes run via Gemini as the subject). **The Layer-1 hard native-write deny is NOT achievable on the agy CLI** — this section supersedes the §3 "native writes hard-denied / un-re-grantable" design intent and resolves §8 F2 as a confirmed negative. David ruled **posture A** (2026-06-02).

**Probe round 1 (settings.json `permissions.deny`):**
- The `deny: [write_file, replace, create_file, edit_file, generate_image, start_subagent]` block was **not retained as an effective control**: after restart the persisted `settings.json` held only `command(...)` (shell) entries (bare tool-names not retained), and even where an agy log parsed the `Deny:[…]` array it **did not enforce native tool calls**. (The approval dialog's "always allow … Persist to settings.json" writes a `command(...)` entry — confirming command-shaped persistence only.) Net: native writes were allowed regardless of the parse.
- With the deny ineffective, the live native writers **`write_file` (`Create`)** and **`replace` (`Edit`)** (SDK doc aliases: `create_file`/`edit_file`) **succeeded with NO prompt** (SDK default policy allows file tools).
- Arbitrary `.venv/bin/python3.14 -c …` (`run_shell_command`) **PROMPTED David** — the §3 allow-list tightening (removing `command(.venv/bin/python3.14)` + `command(.venv/bin/pytest)`) **DID take and persists**. The shell hole is closed.
- The §5 hygiene tripwire **flagged the probe write** (`?? scripts/_AGY_WRITE_PROBE_DELETEME.txt`, exit 1) — detection works.

**Probe round 2 (project-config `gitFolder.allowWrite`, Codex lead):** set `gitFolder.allowWrite: false` on the active project config (`b35a02a0`, confirmed bound in the post-restart log; the flag *survived* restart, unlike the settings deny). `create_file`/`replace` **still succeeded**; reads still worked. `gitFolder.allowWrite` is git-folder-write semantics, **not** `write_file`-tool permission (and agy reads projects "via cache"). The edit was reverted to the original plain-folder resource.

**Config surface exhausted:** `settings.json` deny (not retained / not enforced), CLI flags (none — only `--dangerously-skip-permissions` [the inverse] and `--sandbox` [terminal-only]), `gitFolder.allowWrite` (not a write-tool gate). **No agy config or flag denies native writes while preserving reads** — `view_file`/`create_file`/`edit_file` are governed together. The only true hard-deny is **Option C** (relaunch Gemini via the Antigravity SDK with `policy.deny("write_file"/"replace"/"create_file"/"edit_file"/…)`), which abandons the interactive `agy` CLI — **NOT chosen** (David: too heavy for a single-user project).

**FINALIZED POSTURE A (David ruling 2026-06-02):**
1. **Shell-lock (settings allow-list)** — persists; arbitrary shell/python prompts David. *Caveat:* never launch agy with `--dangerously-skip-permissions` (it drops this and auto-approves everything).
2. **Hygiene tripwire = MANDATORY gate** — Claude/Codex run `.venv/bin/python3.14 scripts/cockpit_hygiene_check.py` (not executable as `./`; add `--allow <glob>` for known in-flight files) before accepting any Gemini source-verification CLEAR and at session boundaries. **This is the native-write enforcement (detection, not prevention).**
3. **Charter (committed P2 `2c9d370`)** — `GEMINI.md` / operating-loop / `dynasty-genius-pm` skill: the read-only mandate + Product Vision.

**Honest statement of enforcement strength:** native file writes are **DETECTED, NOT PREVENTED**. This is a real improvement over the pre-breach state (the silent-script/shell hole is closed; detection exists; the role is sharpened and enforced where the platform allows), but it is **not** an absolute write-prevention wall. Any prior "hard-denied / un-re-grantable" language in this spec is superseded by this section.

**P2 doc reconciliation (BUNDLED into this amendment):** the `GEMINI.md` / operating-loop charter language committed in P2 (`2c9d370`) had stated native writes were "tool-denied." This amendment reconciles both to the posture-A truth — **shell prompt-gated; native writes prohibited-by-mandate + `cockpit_hygiene_check.py`-tripwire-detected (not config-deniable on agy)**; the mandatory-tripwire-gate rule is recorded in the operating-loop. The *scope* (read-only PM, no implementation writes) is unchanged and correct.
