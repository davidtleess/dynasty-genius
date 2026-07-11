# Sources (DG's artifacts, not SaaS connectors)

The upstream plugin pulled context from Slack, Linear, Notion, Figma, Amplitude, Intercom, and Fireflies. Dynasty Genius has none of those and wants none of them — it is local-first with tight data boundaries. Instead, these skills read and write DG's own repo artifacts. When a skill says "pull context," it means these.

| DG source | Path / access | Used by |
|---|---|---|
| **Sprint state / roadmap** | `AGENT_SYNC.md` (living status; most-recent at top) | roadmap-update, david-update, write-spec |
| **Session log** | `docs/agent-ledger/YYYY-MM-DD.md` (per-agent entries) | david-update, roadmap-update, all |
| **Governance (immutable)** | `docs/governance/00-product-constitution.md` (football rules + No-Verdict), `01-north-star-architecture.md`, `02-agent-operating-loop.md`, `03-code-hygiene-policy.md`, `04-strategic-execution-charter.md` | write-spec, all |
| **Specs of record** | `docs/superpowers/specs/YYYY-MM-DD-<slug>-design.md` | write-spec |
| **Plans** | `docs/superpowers/plans/` | write-spec, roadmap-update |
| **Design law (frontend)** | root `PRODUCT.md` + `DESIGN.md`; the `impeccable` skill | write-spec (visual surfaces) |
| **Research corpus** | `docs/strategies/` (incl. `UI Research/`), edge-patterns briefs | synthesize-research |
| **Cross-session memory** | the session auto-memory (user-private, **outside the repo**; `MEMORY.md` index within it) — *if present* | all (recall; verify before relying) |
| **Version control / CI** | GitHub via `gh` (PRs, `gh pr checks`); CI is the merge gate, not local-green | david-update, roadmap-update |
| **The cockpit** | Codex (`dynasty:1.2`) + Gemini (`dynasty:1.3`) via `scripts/tmux_msg.py` — Codex authors REDs and reviews; Gemini is advisory/non-binding | write-spec, synthesize-research |
| **Model / operational telemetry** | `GET /api/system/capture-health`, `/api/system/model-provenance`, `/api/health`, realized-outcome scorecard, the forward-capture SQLite stores | metrics-review |
| **Tests** | `.venv/bin/python3.14 -m pytest` (see `AGENT_SYNC.md` for the exclusion list) | write-spec, metrics-review |

## Rules for reading sources

- **Verify, don't trust.** Recalled memory and Gemini claims reflect what was true when written and are non-binding — confirm a file/flag/route still exists before relying on it.
- **Evidence-grade everything.** Cite data as-of-fetch. The validation ladder (Hypothesis → Provisional → Validated) never flips `decision_supported`.
- **No new connectors without David.** Do not propose wiring DG to an external SaaS. If a source is missing, say so and work from what's provided.
