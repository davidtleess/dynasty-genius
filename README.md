# Dynasty Genius

Personal dynasty fantasy football intelligence system for David's primary Superflex PPR league.

## Mandatory Agent Start

Before working in this repository, agents must read:

1. `docs/governance/02-agent-operating-loop.md`
2. `docs/governance/00-product-constitution.md`
2a. `docs/governance/05-layer-doctrine.md` — **ALWAYS, EVERY SESSION. Read it; it is short.** **Do not rely on any summary of it, including this pointer** — §1 forbids paraphrase, so the doctrine's own words are supplied only by the mandatory read. §1 is David's words verbatim; §2 onward is agent-authored codification — cite them differently and never attribute the whole file to him. His ruling, quoted exactly: *"Steps 1 and 2 are the foundation - if we don't have this our app WILL NOT WORK. we shouldn't be wasting cycles until we've built this foundation."* **Obligations (pending — see ACTIVATION STATUS at the end of this item):** name the layer your work serves in every preflight; work at layers 3-6 records the layers 1-2 dependency check (what you ran, what it showed, your conclusion). Priority is never authorization, and a conclusion is not a licence to fix. **ACTIVATION STATUS — read this before treating anything in this item as binding.** **`05` §1 is David's own words and stands on his authority.** But **the every-session read requirement AND the obligations stated above are BOTH agent-authored codification, PENDING DAVID'S RATIFICATION and NOT YET BINDING** — he never issued a read command; that delivery mechanism is ours. The lanes follow both voluntarily pending his word, but no agent may cite either as law, hold another agent to them, or block work on them until he ratifies. Ratification is tracked on `AGENT_SYNC.md`.
3. `docs/governance/01-north-star-architecture.md`
4. `docs/governance/03-code-hygiene-policy.md`
5. `PRODUCT.md` and `DESIGN.md` when the task touches frontend, UI, CSS, components, or any visual surface
6. `AGENT_SYNC.md`

The governance docs are the canonical operating system for this project.

## Stack

- Backend: FastAPI / Python
- Data and modeling: `nfl_data_py`, scikit-learn, versioned artifacts
- Data sources: Sleeper, PlayerProfiler, PFF, KTC overlay, RAS, Pro Football Reference

## Structure

- `app/api/` route handlers
- `app/services/` business logic
- `app/data/` external API clients, scrapers, pipelines, and model artifacts
- `app/models/` Pydantic models
- `docs/governance/` binding product and agent doctrine
- `docs/agent-ledger/` cross-agent session logs

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```
