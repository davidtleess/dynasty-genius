# Roster Audit Increment 2 — Read-Only UI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the empty "Roster Audit" nav slot in `AppShell` into a read-only, honesty-first UI surface over `GET /api/roster/audit` (typed `RosterAuditResponse`).

**Architecture:** New `frontend/src/roster/` folder following the shipped-surface pattern (`trust/`, `trade/`). A container owns a discriminated-union state machine (loading / active / degraded / config-error / unavailable / parse-error / empty) sourced from a manual `fetch()` + generated Zod parse (no callable client — `@hey-api` emits types+schemas only). Presentational children render the honesty header, faithful table with inline row-expand, and the QB context section. One backend integration test closes the Inc1 real-PVO follow-up (backend half).

**Tech Stack:** Vite + React + TS, Zod (`zRosterAuditResponse`), vitest + @testing-library/react (`// @vitest-environment jsdom`), Biome lint, FastAPI/pytest (backend test). Stack A, no new runtime deps.

**Spec:** `docs/superpowers/specs/2026-06-19-roster-audit-increment-2-ui-design.md` (dual-CLEARED, committed `584c5ab`).

---

## File Structure

- Create `frontend/src/roster/fixtures.ts` — typed `RosterAuditResponse` fixtures (incl. a real-`assemble_pvo()`-shaped one).
- Create `frontend/src/roster/RosterAuditStates.tsx` — loading / config-error (422) / unavailable (503) / parse-error / empty presentational states.
- Create `frontend/src/roster/RosterAuditHeader.tsx` — honesty header (status, per-position `model_status`, caveats, dropped-count, disclaimer).
- Create `frontend/src/roster/RosterAuditRow.tsx` — one player row + inline expand detail.
- Create `frontend/src/roster/RosterAuditTable.tsx` — table shell + column headers + rows.
- Create `frontend/src/roster/QbContextSection.tsx` — QB context cards.
- Create `frontend/src/roster/RosterAudit.tsx` — container: fetch + Zod parse + state machine + composition.
- Create `frontend/src/roster/RosterAudit.css` — surface styles (uses `styles/tokens.css`).
- Create test files `frontend/src/roster/*.test.jsx` (colocated).
- Modify `frontend/src/shell/AppShell.tsx` — render `<RosterAudit />` for the Roster Audit surface.
- Create `tests/contract/test_roster_audit_integration.py` — real `assemble_pvo()` → `assemble_response()` (Inc1 follow-up backend half).

**Type reference (Inc1 contract, from `app/api/routes/roster_audit_models.py`, generated into `types.gen.ts`/`zod.gen.ts`):**
`RosterAuditResponse { status: "active"|"degraded"; engine: string; reason: string; model_status_by_position: Record<string,"VALIDATED"|"PROVISIONAL"|"EXPERIMENTAL">; caveats: string[]; players: RosterAuditPlayer[]; qb_context_cards: QbContextCard[]; dropped_player_count: number; decision_supported: false }`.
`RosterAuditPlayer { player_id, full_name, position, nfl_team?, age?, model_grade, model_status_applies, dynasty_value_score?, dvs_pct?, projection_1y?/2y?/3y?, xvar?, signal_completeness, counter_argument: {text?,status,caveats}, top_drivers: {items,caveats}, risk_flags: {items,caveats}, caveats: string[], roster_audit?: { cliff_age?, years_to_cliff?, age_cliff_risk?, biological_debt_score?, liquidity_risk?, signal?, signal_drivers, age_value_context?, caveats } | null, ... }`.
`QbContextCard { player_id, full_name, identity_coverage, context_role, epa_per_dropback?, cpoe?, dakota?, dropback_count?, pass_attempts?, qb_context_annotations, qb_context_caveats, source_qb_context_annotations }`.

---

## Task 1: Typed fixtures (incl. real-PVO shape)

**Files:** Create `frontend/src/roster/fixtures.ts`; Test `frontend/src/roster/fixtures.test.jsx`

- [ ] **Step 1: Write the failing test**

```jsx
// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { zRosterAuditResponse } from "../lib/api/zod.gen";
import { activeAudit, degradedAudit, realPvoAudit, emptyAudit } from "./fixtures";

describe("roster audit fixtures", () => {
  it("every fixture validates against the generated Zod schema", () => {
    for (const fx of [activeAudit(), degradedAudit(), realPvoAudit(), emptyAudit()]) {
      expect(() => zRosterAuditResponse.parse(fx)).not.toThrow();
    }
  });

  it("realPvoAudit carries free-text caveats and no market fields (Inc1 shape)", () => {
    const p = realPvoAudit().players[0];
    expect(p.caveats.some((c) => c.includes(" "))).toBe(true); // free-text sentence
    expect(JSON.stringify(p)).not.toContain("market_overlay");
    expect(JSON.stringify(p)).not.toContain("market_value");
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm --prefix frontend run test -- src/roster/fixtures.test.jsx`
Expected: FAIL — cannot resolve `./fixtures`.

- [ ] **Step 3: Write the fixtures**

```ts
// frontend/src/roster/fixtures.ts
import type { RosterAuditResponse } from "../lib/api";

function player(overrides: Partial<NonNullable<RosterAuditResponse["players"]>[number]> = {}) {
  return {
    player_id: "p1", full_name: "Active WR", position: "WR", nfl_team: "NYJ",
    age: 27, is_prospect: false, engine_used: "engine_b", model_version: "engine_b_v2",
    model_grade: "ACTIVE_B", model_status_applies: true,
    dynasty_value_score: 78.5, projection_1y: 12.3, projection_2y: 11.1,
    projection_3y: 9.8, xvar: 4.2, dvs_pct: 81.0, signal_completeness: 0.86,
    inputs_present: ["target_share"], inputs_missing: [],
    counter_argument: { text: "Solid floor", status: "available", caveats: [] },
    top_drivers: { items: ["target_share"], caveats: [] },
    risk_flags: { items: ["snap_share_below_40pct"], caveats: [] },
    caveats: ["no_market_overlay"],
    roster_audit: {
      cliff_age: 28, years_to_cliff: 1, age_cliff_risk: 0.4,
      biological_debt_score: 0.2, liquidity_risk: "LOW", signal: "approaching_cliff",
      signal_drivers: ["age_within_two_years_of_position_cliff"],
      age_value_context: "approaching_cliff_high_projection",
      caveats: ["no_market_overlay"], decision_supported: false,
    },
    decision_supported: false,
    ...overrides,
  };
}

export function activeAudit(): RosterAuditResponse {
  return {
    status: "active", engine: "pvo_assembler_v1", reason: "ok",
    model_status_by_position: { WR: "VALIDATED", QB: "PROVISIONAL" },
    caveats: ["no_market_overlay"],
    players: [player(), player({ player_id: "p2", full_name: "QB One", position: "QB",
      model_status_applies: true })],
    qb_context_cards: [{
      player_id: "p2", full_name: "QB One", identity_coverage: "FULL",
      context_role: "context_signal", epa_per_dropback: 0.12, cpoe: 1.4,
      dakota: 0.05, dropback_count: 540, pass_attempts: 500,
      qb_context_annotations: ["low_td_int_ratio_bust_context"],
      qb_context_caveats: ["p2s_context_unavailable"],
      source_qb_context_annotations: "cfbd_qb_context_annotations",
      decision_supported: false,
    }],
    dropped_player_count: 0, decision_supported: false,
  };
}

export function degradedAudit(): RosterAuditResponse {
  return { ...activeAudit(), status: "degraded",
    model_status_by_position: { WR: "EXPERIMENTAL" },
    caveats: ["no_market_overlay", "trust_status_unavailable", "player_row_dropped_corrupt"],
    dropped_player_count: 1 };
}

export function emptyAudit(): RosterAuditResponse {
  return { status: "active", engine: "pvo_assembler_v1", reason: "ok",
    model_status_by_position: {}, caveats: ["no_market_overlay"],
    players: [], qb_context_cards: [], dropped_player_count: 0, decision_supported: false };
}

// Shaped like a real assemble_pvo() PRE_MODEL veteran row: flat fields, free-text
// caveats, market fields already excluded by the Inc1 allowlist mapper.
export function realPvoAudit(): RosterAuditResponse {
  return { ...activeAudit(),
    players: [player({
      player_id: "vet1", full_name: "Vet RB", position: "RB", model_grade: "PRE_MODEL",
      model_status_applies: false, dynasty_value_score: null, projection_1y: null,
      projection_2y: null, projection_3y: null, xvar: null, dvs_pct: null,
      signal_completeness: 0.24,
      caveats: [
        "dynasty_value_score unavailable: Engine B (active player) not yet validated; model_grade is PRE_MODEL",
        "Fewer than 50% of required signals present — do not use for dynasty decisions until data is refreshed",
        "no_market_overlay",
      ],
    })],
    model_status_by_position: { RB: "EXPERIMENTAL" } };
}
```

- [ ] **Step 4: Run to verify pass** — same command → PASS.
- [ ] **Step 5: Commit** — `git add frontend/src/roster/fixtures.ts frontend/src/roster/fixtures.test.jsx && git commit -m "feat(roster-ui): typed roster-audit fixtures incl. real-PVO shape (Inc2 T1)"`

---

## Task 2: RosterAuditStates (loading / 422 / 503 / parse-error / empty)

**Files:** Create `frontend/src/roster/RosterAuditStates.tsx`; Test `frontend/src/roster/RosterAuditStates.test.jsx`

- [ ] **Step 1: Write the failing test**

```jsx
// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LoadingState, ConfigErrorState, UnavailableState, ParseErrorState, EmptyState } from "./RosterAuditStates";

describe("RosterAuditStates", () => {
  it("renders each honest state with no blank output", () => {
    render(<LoadingState />); expect(screen.getByText(/loading roster audit/i)).toBeTruthy();
    render(<ConfigErrorState />); expect(screen.getByText(/roster not configured/i)).toBeTruthy();
    render(<UnavailableState />); expect(screen.getByText(/roster data unavailable/i)).toBeTruthy();
    render(<ParseErrorState />); expect(screen.getByText(/could not read roster audit/i)).toBeTruthy();
    render(<EmptyState />); expect(screen.getByText(/no rostered skill players/i)).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `npm --prefix frontend run test -- src/roster/RosterAuditStates.test.jsx` → FAIL (module missing).

- [ ] **Step 3: Implement**

```tsx
// frontend/src/roster/RosterAuditStates.tsx
function Notice({ title, body }: { title: string; body: string }) {
  return (
    <div className="dg-roster__state" role="status">
      <p className="dg-roster__state-title">{title}</p>
      <p className="dg-roster__state-body">{body}</p>
    </div>
  );
}

export const LoadingState = () => <Notice title="Loading roster audit" body="Fetching your roster from the model." />;
export const ConfigErrorState = () => <Notice title="Roster not configured" body="The league/roster configuration is missing or invalid." />;
export const UnavailableState = () => <Notice title="Roster data unavailable" body="The roster audit dependency is temporarily unavailable." />;
export const ParseErrorState = () => <Notice title="Could not read roster audit" body="The response did not match the expected contract." />;
export const EmptyState = () => <Notice title="No rostered skill players" body="No QB/RB/WR/TE players were returned for your roster." />;
```

- [ ] **Step 4: Run to verify pass** — same command → PASS.
- [ ] **Step 5: Commit** — `git add frontend/src/roster/RosterAuditStates.tsx frontend/src/roster/RosterAuditStates.test.jsx && git commit -m "feat(roster-ui): honest non-success states (Inc2 T2)"`

---

## Task 3: RosterAuditHeader (honesty header)

**Files:** Create `frontend/src/roster/RosterAuditHeader.tsx`; Test `frontend/src/roster/RosterAuditHeader.test.jsx`

- [ ] **Step 1: Write the failing test**

```jsx
// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RosterAuditHeader } from "./RosterAuditHeader";
import { degradedAudit } from "./fixtures";

describe("RosterAuditHeader", () => {
  it("shows status, per-position model_status, caveats, dropped count, disclaimer", () => {
    const a = degradedAudit();
    render(<RosterAuditHeader status={a.status} modelStatusByPosition={a.model_status_by_position}
      caveats={a.caveats} droppedPlayerCount={a.dropped_player_count} />);
    expect(screen.getByText(/degraded/i)).toBeTruthy();
    expect(screen.getByText("WR")).toBeTruthy();
    expect(screen.getByText("EXPERIMENTAL")).toBeTruthy();
    expect(screen.getByText(/1 .*dropped/i)).toBeTruthy();
    expect(screen.getByText(/experimental — not decision-grade/i)).toBeTruthy();
    expect(screen.getByText(/no_market_overlay/)).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `... src/roster/RosterAuditHeader.test.jsx` → FAIL.

- [ ] **Step 3: Implement**

```tsx
// frontend/src/roster/RosterAuditHeader.tsx
import type { RosterAuditResponse } from "../lib/api";

type Props = {
  status: RosterAuditResponse["status"];
  modelStatusByPosition: NonNullable<RosterAuditResponse["model_status_by_position"]>;
  caveats: string[];
  droppedPlayerCount: number;
};

export function RosterAuditHeader({ status, modelStatusByPosition, caveats, droppedPlayerCount }: Props) {
  return (
    <header className="dg-roster__header" aria-label="Roster audit status">
      <div className="dg-roster__status" data-status={status}>
        Status: <strong>{status}</strong>
      </div>
      <p className="dg-roster__disclaimer">Experimental — not decision-grade.</p>
      <ul className="dg-roster__model-status">
        {Object.entries(modelStatusByPosition).map(([pos, st]) => (
          <li key={pos} className="dg-roster__chip" data-status={st}>
            <span>{pos}</span> <span>{st}</span>
          </li>
        ))}
      </ul>
      {droppedPlayerCount > 0 && (
        <p className="dg-roster__dropped">{droppedPlayerCount} row(s) dropped (corrupt/unmappable).</p>
      )}
      {caveats.length > 0 && (
        <ul className="dg-roster__caveats">
          {caveats.map((c) => <li key={c}>{c}</li>)}
        </ul>
      )}
    </header>
  );
}
```

- [ ] **Step 4: Run to verify pass** — same command → PASS.
- [ ] **Step 5: Commit** — `git add frontend/src/roster/RosterAuditHeader.tsx frontend/src/roster/RosterAuditHeader.test.jsx && git commit -m "feat(roster-ui): honesty header (Inc2 T3)"`

---

## Task 4: RosterAuditRow + RosterAuditTable (faithful table + row-expand)

**Files:** Create `frontend/src/roster/RosterAuditRow.tsx`, `frontend/src/roster/RosterAuditTable.tsx`; Test `frontend/src/roster/RosterAuditTable.test.jsx`

- [ ] **Step 1: Write the failing test**

```jsx
// @vitest-environment jsdom
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RosterAuditTable } from "./RosterAuditTable";
import { activeAudit, realPvoAudit } from "./fixtures";

describe("RosterAuditTable", () => {
  it("renders one row per player in contract order with primary columns", () => {
    render(<RosterAuditTable players={activeAudit().players} />);
    const rows = within(screen.getByRole("table")).getAllByRole("row").slice(1);
    expect(rows.length).toBe(2);
    expect(within(rows[0]).getByText("Active WR")).toBeTruthy();
    expect(within(rows[0]).getByText(/VALIDATED|PROVISIONAL|EXPERIMENTAL|ACTIVE_B/)).toBeTruthy();
  });

  it("shows '—' for absent scores and de-emphasizes non-applicable rows", () => {
    render(<RosterAuditTable players={realPvoAudit().players} />);
    const row = within(screen.getByRole("table")).getAllByRole("row")[1];
    expect(within(row).getByText("—")).toBeTruthy();
    expect(row.getAttribute("data-applies")).toBe("false");
  });

  it("row-expand reveals detail (counter-argument, drivers, full caveats)", () => {
    render(<RosterAuditTable players={realPvoAudit().players} />);
    fireEvent.click(screen.getByRole("button", { name: /expand vet rb/i }));
    expect(screen.getByText(/do not use for dynasty decisions/i)).toBeTruthy();
  });

  it("uses neutral, non-verdict column labels (no verdict vocabulary)", () => {
    const { container } = render(<RosterAuditTable players={activeAudit().players} />);
    const headerText = container.querySelector("thead")?.textContent ?? "";
    expect(headerText).not.toMatch(/\b(sell|buy|hold|drop now|must|tier|win|loss)\b/i);
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `... src/roster/RosterAuditTable.test.jsx` → FAIL.

- [ ] **Step 3: Implement the row**

```tsx
// frontend/src/roster/RosterAuditRow.tsx
import { useState } from "react";
import type { RosterAuditResponse } from "../lib/api";

type Player = NonNullable<RosterAuditResponse["players"]>[number];
const num = (v: number | null | undefined) => (v == null ? "—" : String(v));

export function RosterAuditRow({ player }: { player: Player }) {
  const [open, setOpen] = useState(false);
  const ra = player.roster_audit;
  // Generated types mark these optional/nullable — normalize before use.
  const caveats = player.caveats ?? [];
  const drivers = player.top_drivers?.items ?? [];
  const risks = player.risk_flags?.items ?? [];
  return (
    <>
      <tr data-applies={String(player.model_status_applies)} data-grade={player.model_grade}>
        <td>
          <button type="button" aria-label={`Expand ${player.full_name}`} onClick={() => setOpen((o) => !o)}>
            {player.full_name}
          </button>
        </td>
        <td>{player.position}</td>
        <td>{player.nfl_team ?? "—"}</td>
        <td>{num(player.age)}</td>
        <td>{player.model_grade}</td>
        <td>{player.model_status_applies ? "applies" : "n/a"}</td>
        <td>{num(player.dynasty_value_score)}{player.dvs_pct != null ? ` (${player.dvs_pct}%)` : ""}</td>
        <td>{ra?.signal ?? "—"}{ra?.years_to_cliff != null ? ` (${ra.years_to_cliff}y)` : ""}</td>
        <td>{Math.round((player.signal_completeness ?? 0) * 100)}%</td>
        <td>{caveats.length}</td>
      </tr>
      {open && (
        <tr className="dg-roster__detail">
          <td colSpan={10}>
            {player.counter_argument?.text && <p>Counter-argument: {player.counter_argument.text}</p>}
            <p>Top drivers: {drivers.join(", ") || "—"}</p>
            <p>Risk flags: {risks.join(", ") || "—"}</p>
            <p>Projections: {num(player.projection_1y)} / {num(player.projection_2y)} / {num(player.projection_3y)}</p>
            <p>xVAR: {num(player.xvar)} · Liquidity: {ra?.liquidity_risk ?? "—"} · Bio-debt: {num(ra?.biological_debt_score)}</p>
            <ul>{caveats.map((c) => <li key={c}>{c}</li>)}</ul>
          </td>
        </tr>
      )}
    </>
  );
}
```

- [ ] **Step 4: Implement the table**

```tsx
// frontend/src/roster/RosterAuditTable.tsx
import type { RosterAuditResponse } from "../lib/api";
import { RosterAuditRow } from "./RosterAuditRow";

const COLUMNS = ["Player", "Pos", "Team", "Age", "Model grade", "Model status", "DVS", "Age signal", "Signal completeness", "Caveats"];

export function RosterAuditTable({ players }: { players: NonNullable<RosterAuditResponse["players"]> }) {
  return (
    <table className="dg-roster__table">
      <thead><tr>{COLUMNS.map((c) => <th key={c}>{c}</th>)}</tr></thead>
      <tbody>{players.map((p) => <RosterAuditRow key={p.player_id} player={p} />)}</tbody>
    </table>
  );
}
```

- [ ] **Step 5: Run to verify pass** — same command → PASS.
- [ ] **Step 6: Commit** — `git add frontend/src/roster/RosterAuditRow.tsx frontend/src/roster/RosterAuditTable.tsx frontend/src/roster/RosterAuditTable.test.jsx && git commit -m "feat(roster-ui): faithful table + row-expand (Inc2 T4)"`

---

## Task 5: QbContextSection

**Files:** Create `frontend/src/roster/QbContextSection.tsx`; Test `frontend/src/roster/QbContextSection.test.jsx`

- [ ] **Step 1: Write the failing test**

```jsx
// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { QbContextSection } from "./QbContextSection";
import { activeAudit } from "./fixtures";

describe("QbContextSection", () => {
  it("renders QB cards labeled context-signal / not decision-grade", () => {
    render(<QbContextSection cards={activeAudit().qb_context_cards} />);
    expect(screen.getByText("QB One")).toBeTruthy();
    expect(screen.getByText(/context signal — not decision-grade/i)).toBeTruthy();
    expect(screen.getByText(/low_td_int_ratio_bust_context/)).toBeTruthy();
  });
  it("renders nothing when there are no cards", () => {
    const { container } = render(<QbContextSection cards={[]} />);
    expect(container.querySelector(".dg-roster__qb")).toBeNull();
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `... src/roster/QbContextSection.test.jsx` → FAIL.

- [ ] **Step 3: Implement**

```tsx
// frontend/src/roster/QbContextSection.tsx
import type { RosterAuditResponse } from "../lib/api";

export function QbContextSection({ cards }: { cards: NonNullable<RosterAuditResponse["qb_context_cards"]> }) {
  const list = cards ?? [];
  if (list.length === 0) return null;
  return (
    <section className="dg-roster__qb" aria-label="QB context cards">
      <h2>QB context</h2>
      <p className="dg-roster__disclaimer">Context signal — not decision-grade.</p>
      <ul>
        {list.map((c) => (
          <li key={c.player_id} className="dg-roster__qb-card" data-coverage={c.identity_coverage}>
            <strong>{c.full_name}</strong>
            <span> EPA/db {c.epa_per_dropback ?? "—"} · CPOE {c.cpoe ?? "—"} · DAKOTA {c.dakota ?? "—"}</span>
            <div>{(c.qb_context_annotations ?? []).join(", ") || "—"}</div>
            <div>{(c.qb_context_caveats ?? []).join(", ") || "—"}</div>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

- [ ] **Step 4: Run to verify pass** — same command → PASS.
- [ ] **Step 5: Commit** — `git add frontend/src/roster/QbContextSection.tsx frontend/src/roster/QbContextSection.test.jsx && git commit -m "feat(roster-ui): QB context section (Inc2 T5)"`

---

## Task 6: RosterAudit container (fetch + Zod parse + state machine)

**Files:** Create `frontend/src/roster/RosterAudit.tsx`, `frontend/src/roster/RosterAudit.css`; Test `frontend/src/roster/RosterAudit.test.jsx`

- [ ] **Step 1: Write the failing test**

```jsx
// @vitest-environment jsdom
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RosterAudit } from "./RosterAudit";
import { activeAudit } from "./fixtures";

function mockFetch(status, body) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: status === 200, status, json: async () => body,
  });
}
afterEach(() => vi.restoreAllMocks());

describe("RosterAudit container", () => {
  it("renders header + table on 200 active", async () => {
    mockFetch(200, activeAudit());
    render(<RosterAudit />);
    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    expect(screen.getByText(/experimental — not decision-grade/i)).toBeTruthy();
  });
  it("renders config-error on 422", async () => {
    mockFetch(422, { detail: { error: "roster_config_error", message: "x" } });
    render(<RosterAudit />);
    await waitFor(() => expect(screen.getByText(/roster not configured/i)).toBeTruthy());
  });
  it("renders unavailable on 503", async () => {
    mockFetch(503, { detail: { error: "roster_dependency_unavailable", message: "x" } });
    render(<RosterAudit />);
    await waitFor(() => expect(screen.getByText(/roster data unavailable/i)).toBeTruthy());
  });
  it("renders parse-error when the body violates the contract", async () => {
    mockFetch(200, { bogus: true });
    render(<RosterAudit />);
    await waitFor(() => expect(screen.getByText(/could not read roster audit/i)).toBeTruthy());
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `... src/roster/RosterAudit.test.jsx` → FAIL.

- [ ] **Step 3: Implement**

```tsx
// frontend/src/roster/RosterAudit.tsx
import { useEffect, useState } from "react";
import { zRosterAuditResponse } from "../lib/api/zod.gen";
import type { RosterAuditResponse } from "../lib/api";
import { QbContextSection } from "./QbContextSection";
import "./RosterAudit.css";
import { RosterAuditHeader } from "./RosterAuditHeader";
import { ConfigErrorState, EmptyState, LoadingState, ParseErrorState, UnavailableState } from "./RosterAuditStates";
import { RosterAuditTable } from "./RosterAuditTable";

type State =
  | { status: "loading" }
  | { status: "ready"; data: RosterAuditResponse }
  | { status: "config-error" }
  | { status: "unavailable" }
  | { status: "parse-error" };

export function RosterAudit() {
  const [state, setState] = useState<State>({ status: "loading" });
  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    (async () => {
      try {
        const res = await fetch("/api/roster/audit");
        if (!res.ok) {
          if (active) setState({ status: res.status === 422 ? "config-error" : "unavailable" });
          return;
        }
        const data = zRosterAuditResponse.parse(await res.json());
        if (active) setState({ status: "ready", data });
      } catch {
        if (active) setState({ status: "parse-error" });
      }
    })();
    return () => { active = false; };
  }, []);

  if (state.status === "loading") return <LoadingState />;
  if (state.status === "config-error") return <ConfigErrorState />;
  if (state.status === "unavailable") return <UnavailableState />;
  if (state.status === "parse-error") return <ParseErrorState />;
  const { data } = state;
  // Generated types mark these optional — normalize before passing to children.
  const players = data.players ?? [];
  const cards = data.qb_context_cards ?? [];
  const caveats = data.caveats ?? [];
  return (
    <div className="dg-roster">
      <RosterAuditHeader status={data.status} modelStatusByPosition={data.model_status_by_position ?? {}}
        caveats={caveats} droppedPlayerCount={data.dropped_player_count ?? 0} />
      {players.length === 0 ? <EmptyState /> : <RosterAuditTable players={players} />}
      <QbContextSection cards={cards} />
    </div>
  );
}
```

- [ ] **Step 4: Write minimal CSS** — create `frontend/src/roster/RosterAudit.css` with class stubs (`.dg-roster`, `.dg-roster__header`, `.dg-roster__chip[data-status="EXPERIMENTAL"]` de-emphasis, `tr[data-applies="false"]` de-emphasis) using `var(--…)` tokens from `styles/tokens.css`. (Visual only; no test.)

- [ ] **Step 5: Run to verify pass** — same command → PASS.
- [ ] **Step 6: Commit** — `git add frontend/src/roster/RosterAudit.tsx frontend/src/roster/RosterAudit.css frontend/src/roster/RosterAudit.test.jsx && git commit -m "feat(roster-ui): container fetch + Zod parse + state machine (Inc2 T6)"`

---

## Task 7: Wire into AppShell

**Files:** Modify `frontend/src/shell/AppShell.tsx`; Test `frontend/src/shell/AppShell.test.jsx`

- [ ] **Step 1: Write the failing test** (append to the existing AppShell test)

```jsx
it("renders the Roster Audit surface when its nav item is selected", () => {
  globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({
    status: "active", engine: "e", reason: "r", model_status_by_position: {},
    caveats: [], players: [], qb_context_cards: [], dropped_player_count: 0, decision_supported: false }) });
  render(<AppShell />);
  fireEvent.click(screen.getByRole("button", { name: "Roster Audit" }));
  expect(screen.getByText(/experimental — not decision-grade/i)).toBeTruthy();
});
```

- [ ] **Step 2: Run to verify it fails** — `npm --prefix frontend run test -- src/shell/AppShell.test.jsx` → FAIL (slot renders only the title).

- [ ] **Step 3: Implement** — in `AppShell.tsx`, add `import { RosterAudit } from "../roster/RosterAudit";` and the render branch beside the existing ones:

```tsx
{activeSurface === "Roster Audit" && <RosterAudit />}
```

- [ ] **Step 4: Run to verify pass** — same command → PASS.
- [ ] **Step 5: Commit** — `git add frontend/src/shell/AppShell.tsx frontend/src/shell/AppShell.test.jsx && git commit -m "feat(roster-ui): wire Roster Audit surface into AppShell (Inc2 T7)"`

---

## Task 8: Backend integration test (Inc1 follow-up, backend half)

**Files:** Create `tests/contract/test_roster_audit_integration.py`

- [ ] **Step 1: Write the characterization/guard test** (NOT RED-first — this locks current correct behavior; it passes on current code and fails only if a future change breaks the real `assemble_pvo` → `assemble_response` mapping)

```python
from src.dynasty_genius.pvo_assembler import assemble_pvo
from src.dynasty_genius.models.player_identity import PlayerIdentity
from app.api.routes.roster_audit_models import assemble_response


def test_real_assemble_pvo_row_maps_through_assemble_response():
    ident = PlayerIdentity(dg_id="x", full_name="Vet WR", position="WR",
        nfl_team="NYJ", sleeper_id="x", verification_status="VERIFIED")
    pvo = assemble_pvo(ident, {"age": 27.0}).dict()
    # Inject leak vectors explicitly so this guards the Inc1 leak follow-up even
    # if a future assemble_pvo stops emitting market_overlay (the real dict already
    # carries market_overlay; market_value/future_x are added to prove the allowlist
    # excludes by construction on a real-shaped row).
    pvo["market_value"] = 999
    pvo["future_x"] = "LEAKVALUE"
    audit = {"status": "active", "engine": "pvo_assembler_v1", "reason": "ok",
        "caveats": ["no_market_overlay"], "players": [pvo], "qb_context_cards": []}

    resp = assemble_response(audit)

    assert len(resp.players) == 1                      # real row maps, not dropped
    blob = resp.model_dump_json()
    assert "market_overlay" not in blob.replace("no_market_overlay", "")
    assert '"market_value"' not in blob
    assert "future_x" not in blob and "LEAKVALUE" not in blob and "999" not in blob
    # free-text PVO caveats survive (not token-stripped)
    assert any(" " in c for c in resp.players[0].caveats)
    assert resp.decision_supported is False
```

- [ ] **Step 2: Run to verify** — `.venv/bin/python3.14 -m pytest tests/contract/test_roster_audit_integration.py -v` → PASS (this is a characterization/guard test; it passes on current code and locks the behavior).

- [ ] **Step 3: Lint** — `.venv/bin/ruff check tests/contract/test_roster_audit_integration.py` → PASS.
- [ ] **Step 4: Commit** — `git add tests/contract/test_roster_audit_integration.py && git commit -m "test(roster-audit): real assemble_pvo -> assemble_response integration guard (Inc2 T8, closes Inc1 follow-up)"`

---

## Task 9: Closeout (FE gate + neutral-copy/banned-vocab + full suites + tollgate)

**Files:** none (verification) + a neutral-copy guard test if the existing banned-vocab gate does not already scan `frontend/src/roster/`

- [ ] **Step 1: Confirm the FE banned-vocabulary gate covers `frontend/src/roster/`.** Inspect the existing banned-language test (it scans authored surface files against `shell/banned_vocabulary.json`). If it scans all of `src/`, no change. If it is per-folder, add `frontend/src/roster/` to its scan list (mirror the existing entry). Run: `npm --prefix frontend run test` and confirm the banned-vocabulary test includes the roster files and passes.

- [ ] **Step 2: Neutral-copy sweep** — the column-label neutral-copy assertion already lives in T4 (`RosterAuditTable.test.jsx`). Here, confirm it passes AND extend the check to the other authored copy: assert the rendered `RosterAuditHeader` chips/labels and `QbContextSection` headings contain no verdict vocabulary `/\b(sell|buy|hold|drop now|must|tier|win|loss)\b/i` (contract-supplied tokens rendered verbatim are exempt — assert against authored labels, not player data).

- [ ] **Step 3: Full FE gate** — `npm --prefix frontend run typecheck && npm --prefix frontend run lint && npm --prefix frontend run test && npm --prefix frontend run build` → all PASS.

- [ ] **Step 4: Full Python suite** — `.venv/bin/python3.14 -m pytest -q` → 0 failed (the new backend test included).

- [ ] **Step 5: OpenAPI drift unchanged** — `.venv/bin/python3.14 -m pytest tests/contract/test_openapi_drift_contract.py -q` → PASS (no contract change).

- [ ] **Step 6: Verifier tollgate (binding, FE + code change)** — `.venv/bin/python3.14 scripts/verify_sprint_closeout.py --base origin/main` → ENFORCE PASS.

- [ ] **Step 7: AC sweep** — confirm AC-1..AC-8 from the spec each map to a passing test/behavior; record in the closeout ledger.

---

## Self-Review (spec coverage)

AC-1 (faithful render) → T4 ✓ · AC-2 (honest trust/degraded; 422/503/parse/empty distinct) → T2+T3+T6 ✓ · AC-3 (no false certainty: model_status_applies chip + EXPERIMENTAL de-emphasis + neutral copy + banned-vocab gate + disclaimer) → T3+T4+T9 ✓ · AC-4 (row-expand detail, verbatim) → T4 ✓ · AC-5 (QB context) → T5 ✓ · AC-6 (Zod parse + defensive 422/503 + parse-error) → T6 ✓ · AC-7 (real-PVO both halves: FE fixture T1/T4 + backend integration T8) → T1+T4+T8 ✓ · AC-8 (no regression / scope: FE gate + Python suite + OpenAPI drift + Inspector/TrustStrip untouched) → T9 ✓. No backend/contract/model change; manual fetch + Zod (no callable client); single model-only lane. Out of scope (sort, filter, mutation, market lane) → no task, by design ✓.
