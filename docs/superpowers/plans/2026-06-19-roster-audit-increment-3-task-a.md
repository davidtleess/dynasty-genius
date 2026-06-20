# Roster Audit — Increment 3, Task A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. In this project the build runs as the cockpit TDD cycle: **Codex authors the RED test → Claude implements GREEN → Codex (technical) + Gemini (governance) dual-CLEAR → David-authorized commit → zero-divergence audit.**

**Goal:** Add client-side sort / filter / grouping controls over the existing Inc2 read-only Roster Audit surface, with zero backend / model / contract / OpenAPI change.

**Architecture:** All ordering/segmentation logic lives in one pure, side-effect-free module (`rosterTransform.ts`) so React components stay "dumb." A new sticky `RosterAuditControls` component drives local UI state in the `RosterAudit` container; the container runs the transform over `response.players` before rendering the (now group-aware) `RosterAuditTable`. The default state is identity-preserving, so the surface still renders the backend's authoritative aging-urgency order on load.

**Tech Stack:** Vite + React + TypeScript; Vitest + @testing-library/react (jsdom) for tests; generated `RosterAuditResponse` type + `zRosterAuditResponse` Zod schema (consumed as-is, no codegen change).

**Revision:** v3 — integrates cockpit review findings: A (disclaimer collision → `getAllByText` in container tests), B (position checkboxes render checked under the empty=All sentinel + toggle materializes All before removing), C (grouped-table avoids `getByText` ambiguity), D (correct closeout gate commands: `npm run banned-language` + Python `test_openapi_drift_contract.py`), E (Task 5 grouped test asserts the `.dg-roster__group-heading` rows directly so it genuinely protects the "heading per group" behavior, not just any "WR"/"QB" text).

## Global Constraints

- **Zero backend / contract / model / OpenAPI change.** Do not modify `app/`, `src/`, or `frontend/openapi.json` / `frontend/src/lib/api/*.gen.ts`. The OpenAPI drift guard must stay green untouched.
- **No new runtime dependencies.**
- **`decision_supported` is never set or overridden by the UI** — it is consumed only.
- **No verdict / action vocabulary** in any label, heading, or copy (no sell/hold/cut/replace/elite/bust/win/loss). The FE banned-vocabulary gate (`frontend/src/shell/banned_vocabulary.json` + its lint/test) must stay clean.
- **Null/missing rows are always visible**, sorted last, never dropped or hidden.
- **No trust-hide filter, no value-band filter/grouping, no Contender-vs-Rebuilding grouping** (deferred; out of contract).
- **Local component state only** — no URL params, no shareable state, resets on reload.
- **EXPERIMENTAL / not-decision-grade disclaimer** stays surfaced; de-emphasis is CSS-only and never reorders rows.
- Player type alias used throughout: `type Player = NonNullable<RosterAuditResponse["players"]>[number];`

---

### Task 1: Pure sort module (`applySort` + null-safe comparators)

**Files:**
- Create: `frontend/src/roster/rosterTransform.ts`
- Test: `frontend/src/roster/rosterTransform.test.js`

**Interfaces:**
- Produces: `type SortKey = "none" | "age_cliff_risk" | "age" | "signal_completeness" | "xvar"`; `function applySort(players: Player[], key: SortKey): Player[]` (returns a new array; `"none"` preserves input order; stable; nulls/non-finite always last regardless of direction).

- [ ] **Step 1: Write the failing test**

```js
// @vitest-environment node
import { describe, expect, it } from "vitest";
import { applySort } from "./rosterTransform";

const mk = (o) => ({
  player_id: o.id, full_name: o.id, position: o.pos ?? "WR",
  is_prospect: o.prospect ?? false, model_grade: "ACTIVE_B",
  age: o.age ?? null, xvar: o.xvar ?? null, signal_completeness: o.sc ?? 0,
  roster_audit: o.ra === undefined ? null : o.ra,
});

describe("applySort", () => {
  it("none preserves input order", () => {
    const ps = [mk({ id: "a" }), mk({ id: "b" }), mk({ id: "c" })];
    expect(applySort(ps, "none").map((p) => p.player_id)).toEqual(["a", "b", "c"]);
  });
  it("age desc, nulls last", () => {
    const ps = [mk({ id: "y", age: 24 }), mk({ id: "n", age: null }), mk({ id: "o", age: 31 })];
    expect(applySort(ps, "age").map((p) => p.player_id)).toEqual(["o", "y", "n"]);
  });
  it("signal_completeness asc (lowest first)", () => {
    const ps = [mk({ id: "hi", sc: 0.9 }), mk({ id: "lo", sc: 0.1 })];
    expect(applySort(ps, "signal_completeness").map((p) => p.player_id)).toEqual(["lo", "hi"]);
  });
  it("xvar desc; negatives below positives; null last", () => {
    const ps = [mk({ id: "neg", xvar: -2 }), mk({ id: "nul", xvar: null }), mk({ id: "pos", xvar: 5 })];
    expect(applySort(ps, "xvar").map((p) => p.player_id)).toEqual(["pos", "neg", "nul"]);
  });
  it("age_cliff_risk desc with tie-breakers; missing roster_audit last", () => {
    const ps = [
      mk({ id: "tieA", ra: { age_cliff_risk: 0.5, years_to_cliff: 3 } }),
      mk({ id: "tieB", ra: { age_cliff_risk: 0.5, years_to_cliff: 1 } }), // earlier cliff -> first on tie
      mk({ id: "low", ra: { age_cliff_risk: 0.2, years_to_cliff: 5 } }),
      mk({ id: "none", ra: null }),
    ];
    expect(applySort(ps, "age_cliff_risk").map((p) => p.player_id)).toEqual(["tieB", "tieA", "low", "none"]);
  });
  it("is stable for fully-equal keys", () => {
    const ps = [mk({ id: "1", age: 25 }), mk({ id: "2", age: 25 }), mk({ id: "3", age: 25 })];
    expect(applySort(ps, "age").map((p) => p.player_id)).toEqual(["1", "2", "3"]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/roster/rosterTransform.test.js`
Expected: FAIL (`applySort` not exported / module missing).

- [ ] **Step 3: Write minimal implementation**

```ts
// frontend/src/roster/rosterTransform.ts
import type { RosterAuditResponse } from "../lib/api";

export type Player = NonNullable<RosterAuditResponse["players"]>[number];

export type SortKey = "none" | "age_cliff_risk" | "age" | "signal_completeness" | "xvar";

function num(v: number | null | undefined): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

// nulls always last, regardless of direction
function cmp(a: number | null, b: number | null, dir: "asc" | "desc"): number {
  if (a === null && b === null) return 0;
  if (a === null) return 1;
  if (b === null) return -1;
  return dir === "asc" ? a - b : b - a;
}

export function applySort(players: Player[], key: SortKey): Player[] {
  if (key === "none") return players.slice();
  const arr = players.slice(); // Array.prototype.sort is stable (ES2019+)
  arr.sort((p1, p2) => {
    switch (key) {
      case "age":
        return cmp(num(p1.age), num(p2.age), "desc");
      case "signal_completeness":
        return cmp(num(p1.signal_completeness), num(p2.signal_completeness), "asc");
      case "xvar":
        return cmp(num(p1.xvar), num(p2.xvar), "desc");
      case "age_cliff_risk": {
        const a1 = p1.roster_audit;
        const a2 = p2.roster_audit;
        let c = cmp(num(a1?.age_cliff_risk), num(a2?.age_cliff_risk), "desc");
        if (c !== 0) return c;
        c = cmp(num(a1?.years_to_cliff), num(a2?.years_to_cliff), "asc");
        if (c !== 0) return c;
        c = cmp(num(p1.age), num(p2.age), "desc");
        if (c !== 0) return c;
        return cmp(num(a1?.biological_debt_score), num(a2?.biological_debt_score), "desc");
      }
      default:
        return 0;
    }
  });
  return arr;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- src/roster/rosterTransform.test.js`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/roster/rosterTransform.ts frontend/src/roster/rosterTransform.test.js
git commit -m "feat(roster): Inc3 Task A — null-safe sort comparators (applySort)"
```

---

### Task 2: Pure filter (`applyFilter`)

**Files:**
- Modify: `frontend/src/roster/rosterTransform.ts`
- Test: `frontend/src/roster/rosterTransform.test.js` (append)

**Interfaces:**
- Produces: `type ProspectFilter = "all" | "active" | "prospects"`; `interface RosterFilterState { positions: string[]; prospect: ProspectFilter }`; `function applyFilter(players: Player[], f: RosterFilterState): Player[]` (empty `positions` = all positions; never returns a blank roster from an empty selection).

- [ ] **Step 1: Write the failing test**

```js
import { applyFilter } from "./rosterTransform";

describe("applyFilter", () => {
  const ps = [
    mk({ id: "wr", pos: "WR", prospect: false }),
    mk({ id: "qb", pos: "QB", prospect: false }),
    mk({ id: "rookie", pos: "RB", prospect: true }),
  ];
  it("empty positions = all", () => {
    expect(applyFilter(ps, { positions: [], prospect: "all" }).map((p) => p.player_id))
      .toEqual(["wr", "qb", "rookie"]);
  });
  it("position multi-select subsets", () => {
    expect(applyFilter(ps, { positions: ["WR", "QB"], prospect: "all" }).map((p) => p.player_id))
      .toEqual(["wr", "qb"]);
  });
  it("prospect=active excludes prospects", () => {
    expect(applyFilter(ps, { positions: [], prospect: "active" }).map((p) => p.player_id))
      .toEqual(["wr", "qb"]);
  });
  it("prospect=prospects keeps only prospects", () => {
    expect(applyFilter(ps, { positions: [], prospect: "prospects" }).map((p) => p.player_id))
      .toEqual(["rookie"]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/roster/rosterTransform.test.js`
Expected: FAIL (`applyFilter` not exported).

- [ ] **Step 3: Write minimal implementation** (append to `rosterTransform.ts`)

```ts
export type ProspectFilter = "all" | "active" | "prospects";

export interface RosterFilterState {
  positions: string[]; // empty = all
  prospect: ProspectFilter;
}

export function applyFilter(players: Player[], f: RosterFilterState): Player[] {
  return players.filter((p) => {
    const posOk = f.positions.length === 0 || f.positions.includes(p.position);
    const prospectOk =
      f.prospect === "all"
        ? true
        : f.prospect === "prospects"
          ? p.is_prospect === true
          : p.is_prospect !== true;
    return posOk && prospectOk;
  });
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- src/roster/rosterTransform.test.js`
Expected: PASS (all Task 1 + Task 2 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/roster/rosterTransform.ts frontend/src/roster/rosterTransform.test.js
git commit -m "feat(roster): Inc3 Task A — applyFilter (position + prospect, empty=all)"
```

---

### Task 3: Pure grouping (`applyGroup`, deterministic group order)

**Files:**
- Modify: `frontend/src/roster/rosterTransform.ts`
- Test: `frontend/src/roster/rosterTransform.test.js` (append)

**Interfaces:**
- Produces: `type GroupKey = "none" | "position" | "depreciation_band"`; `interface RosterGroup { key: string; label: string; players: Player[] }`; `function applyGroup(players: Player[], key: GroupKey, sortKey: SortKey): RosterGroup[]`. Position groups in first-seen backend order; depreciation-band in fixed token-severity order with the "Missing age signal" bucket always last; within-group ordering = `applySort(..., sortKey)`. Group order never depends on `sortKey`.

- [ ] **Step 1: Write the failing test**

```js
import { applyGroup } from "./rosterTransform";

describe("applyGroup", () => {
  it("position groups in first-seen backend order; group order independent of sort", () => {
    const ps = [
      mk({ id: "wr1", pos: "WR", xvar: 1 }),
      mk({ id: "qb1", pos: "QB", xvar: 99 }), // highest xVAR but QB seen after WR
      mk({ id: "wr2", pos: "WR", xvar: 50 }),
    ];
    const groups = applyGroup(ps, "position", "xvar");
    expect(groups.map((g) => g.key)).toEqual(["WR", "QB"]); // first-seen, NOT xVAR-driven
    expect(groups[0].players.map((p) => p.player_id)).toEqual(["wr2", "wr1"]); // sorted within group
  });
  it("depreciation_band uses producer token severity order; missing last", () => {
    const ps = [
      mk({ id: "noSig", ra: null }),
      mk({ id: "appr", ra: { signal: "approaching_cliff" } }),
      mk({ id: "past", ra: { signal: "past_cliff" } }),
      mk({ id: "far", ra: { signal: "no_age_signal" } }),
      mk({ id: "at", ra: { signal: "at_cliff" } }),
    ];
    const groups = applyGroup(ps, "depreciation_band", "none");
    expect(groups.map((g) => g.label)).toEqual([
      "Past cliff age", "At cliff age", "Approaching cliff",
      "3+ years (No immediate cliff)", "Missing age signal",
    ]);
  });
  it("none returns a single unlabeled group, sorted", () => {
    const ps = [mk({ id: "a", age: 20 }), mk({ id: "b", age: 30 })];
    const groups = applyGroup(ps, "none", "age");
    expect(groups.length).toBe(1);
    expect(groups[0].players.map((p) => p.player_id)).toEqual(["b", "a"]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/roster/rosterTransform.test.js`
Expected: FAIL (`applyGroup` not exported).

- [ ] **Step 3: Write minimal implementation** (append to `rosterTransform.ts`)

```ts
export type GroupKey = "none" | "position" | "depreciation_band";

export interface RosterGroup {
  key: string;
  label: string;
  players: Player[];
}

const BAND_ORDER: { token: string; label: string }[] = [
  { token: "past_cliff", label: "Past cliff age" },
  { token: "at_cliff", label: "At cliff age" },
  { token: "approaching_cliff", label: "Approaching cliff" },
  { token: "no_age_signal", label: "3+ years (No immediate cliff)" },
];
const MISSING_BAND = { key: "__missing_age_signal__", label: "Missing age signal" };

export function applyGroup(players: Player[], key: GroupKey, sortKey: SortKey): RosterGroup[] {
  if (key === "none") {
    return [{ key: "__all__", label: "", players: applySort(players, sortKey) }];
  }
  if (key === "position") {
    const order: string[] = [];
    const buckets = new Map<string, Player[]>();
    for (const p of players) {
      if (!buckets.has(p.position)) {
        buckets.set(p.position, []);
        order.push(p.position);
      }
      buckets.get(p.position)!.push(p);
    }
    return order.map((pos) => ({
      key: pos,
      label: pos,
      players: applySort(buckets.get(pos)!, sortKey),
    }));
  }
  // depreciation_band
  const buckets = new Map<string, Player[]>();
  for (const p of players) {
    const sig = p.roster_audit?.signal ?? null;
    const token = BAND_ORDER.find((b) => b.token === sig)?.token ?? MISSING_BAND.key;
    if (!buckets.has(token)) buckets.set(token, []);
    buckets.get(token)!.push(p);
  }
  const groups: RosterGroup[] = [];
  for (const b of BAND_ORDER) {
    const rows = buckets.get(b.token);
    if (rows) groups.push({ key: b.token, label: b.label, players: applySort(rows, sortKey) });
  }
  const missing = buckets.get(MISSING_BAND.key);
  if (missing) {
    groups.push({ key: MISSING_BAND.key, label: MISSING_BAND.label, players: applySort(missing, sortKey) });
  }
  return groups;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- src/roster/rosterTransform.test.js`
Expected: PASS (Tasks 1–3).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/roster/rosterTransform.ts frontend/src/roster/rosterTransform.test.js
git commit -m "feat(roster): Inc3 Task A — applyGroup with deterministic group order"
```

---

### Task 4: Sticky controls component (`RosterAuditControls`)

**Files:**
- Create: `frontend/src/roster/RosterAuditControls.tsx`
- Modify: `frontend/src/roster/RosterAudit.css` (sticky toolbar styles)
- Test: `frontend/src/roster/RosterAuditControls.test.jsx`

**Interfaces:**
- Consumes: `SortKey`, `GroupKey`, `ProspectFilter` from `rosterTransform`.
- Produces: `RosterAuditControls` with props `{ sortKey, groupBy, positions (selected), prospect, allPositions: string[], filteredOutCount: number, onChange(next), onReset() }`. Renders a `Sort by` `<select>`, a `Group by` `<select>`, position checkboxes, a prospect `<select>`, a compact "Experimental — not decision-grade" disclaimer, and (when `filteredOutCount > 0`) a filtered-out count + Reset button. All labels neutral.

- [ ] **Step 1: Write the failing test**

```jsx
// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RosterAuditControls } from "./RosterAuditControls";

const base = {
  sortKey: "none", groupBy: "none", positions: [], prospect: "all",
  allPositions: ["QB", "RB", "WR", "TE"], filteredOutCount: 0,
  onChange: () => {}, onReset: () => {},
};

describe("RosterAuditControls", () => {
  it("renders sort, group, prospect controls and the compact disclaimer", () => {
    render(<RosterAuditControls {...base} />);
    expect(screen.getByLabelText(/sort by/i)).toBeTruthy();
    expect(screen.getByLabelText(/group by/i)).toBeTruthy();
    expect(screen.getByText(/experimental — not decision-grade/i)).toBeTruthy();
  });
  it("emits sort change", () => {
    const onChange = vi.fn();
    render(<RosterAuditControls {...base} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText(/sort by/i), { target: { value: "xvar" } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ sortKey: "xvar" }));
  });
  it("shows filtered-out count + reset only when rows are filtered out", () => {
    const onReset = vi.fn();
    const { rerender } = render(<RosterAuditControls {...base} filteredOutCount={0} />);
    expect(screen.queryByRole("button", { name: /reset/i })).toBeNull();
    rerender(<RosterAuditControls {...base} filteredOutCount={3} onReset={onReset} />);
    expect(screen.getByText(/3 .*filtered out/i)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /reset/i }));
    expect(onReset).toHaveBeenCalled();
  });
  it("default All (positions=[]) shows every checkbox checked; toggling one off excludes only it (finding B)", () => {
    const onChange = vi.fn();
    render(<RosterAuditControls {...base} positions={[]} onChange={onChange} />);
    const boxes = screen.getAllByRole("checkbox");
    expect(boxes.length).toBe(4);
    expect(boxes.every((b) => b.checked)).toBe(true); // empty=All renders all checked
    fireEvent.click(screen.getByLabelText("QB"));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ positions: ["RB", "WR", "TE"] }), // QB excluded, others kept
    );
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/roster/RosterAuditControls.test.jsx`
Expected: FAIL (component missing).

- [ ] **Step 3: Write minimal implementation**

```tsx
// frontend/src/roster/RosterAuditControls.tsx
import type { GroupKey, ProspectFilter, SortKey } from "./rosterTransform";

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "none", label: "Default (aging urgency)" },
  { value: "age_cliff_risk", label: "Age-cliff risk" },
  { value: "age", label: "Age" },
  { value: "signal_completeness", label: "Signal completeness" },
  { value: "xvar", label: "Value above replacement (xVAR)" },
];
const GROUP_OPTIONS: { value: GroupKey; label: string }[] = [
  { value: "none", label: "None" },
  { value: "position", label: "Position" },
  { value: "depreciation_band", label: "Depreciation band" },
];
const PROSPECT_OPTIONS: { value: ProspectFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "active", label: "Active" },
  { value: "prospects", label: "Prospects" },
];

export interface ControlsState {
  sortKey: SortKey;
  groupBy: GroupKey;
  positions: string[];
  prospect: ProspectFilter;
}

export function RosterAuditControls(props: ControlsState & {
  allPositions: string[];
  filteredOutCount: number;
  onChange: (next: ControlsState) => void;
  onReset: () => void;
}) {
  const { sortKey, groupBy, positions, prospect, allPositions, filteredOutCount, onChange, onReset } = props;
  const state: ControlsState = { sortKey, groupBy, positions, prospect };
  // positions === [] is the "All" sentinel. Materialize it before toggling so the
  // UI never shows "all included" while every checkbox reads unchecked (finding B).
  const togglePos = (pos: string) => {
    const current = positions.length === 0 ? allPositions : positions;
    const next = current.includes(pos)
      ? current.filter((p) => p !== pos)
      : [...current, pos];
    // empty OR full selection both normalize back to the All sentinel ([]),
    // honoring the D3 "empty = All, never blank roster" lock.
    const normalized = next.length === 0 || next.length === allPositions.length ? [] : next;
    onChange({ ...state, positions: normalized });
  };

  return (
    <div className="dg-roster__controls">
      <label>
        Sort by
        <select value={sortKey} onChange={(e) => onChange({ ...state, sortKey: e.target.value as SortKey })}>
          {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </label>
      <label>
        Group by
        <select value={groupBy} onChange={(e) => onChange({ ...state, groupBy: e.target.value as GroupKey })}>
          {GROUP_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </label>
      <fieldset className="dg-roster__pos">
        <legend>Position</legend>
        {allPositions.map((pos) => (
          <label key={pos}>
            <input
              type="checkbox"
              checked={positions.length === 0 || positions.includes(pos)}
              onChange={() => togglePos(pos)}
            />
            {pos}
          </label>
        ))}
      </fieldset>
      <label>
        Players
        <select value={prospect} onChange={(e) => onChange({ ...state, prospect: e.target.value as ProspectFilter })}>
          {PROSPECT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </label>
      <span className="dg-roster__controls-disclaimer">Experimental — not decision-grade.</span>
      {filteredOutCount > 0 && (
        <span className="dg-roster__filtered-note" role="status">
          {filteredOutCount} rows filtered out
          <button type="button" onClick={onReset}>Reset</button>
        </span>
      )}
    </div>
  );
}
```

Append to `frontend/src/roster/RosterAudit.css`:

```css
.dg-roster__controls {
  position: sticky;
  top: 0;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
  padding: 0.5rem 0;
  background: var(--dg-surface, #fff);
  border-bottom: 1px solid var(--dg-border, #ddd);
}
.dg-roster__controls-disclaimer { font-size: 0.85rem; opacity: 0.8; }
.dg-roster__pos { display: flex; gap: 0.5rem; border: none; }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- src/roster/RosterAuditControls.test.jsx`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/roster/RosterAuditControls.tsx frontend/src/roster/RosterAuditControls.test.jsx frontend/src/roster/RosterAudit.css
git commit -m "feat(roster): Inc3 Task A — sticky controls toolbar with persistent disclaimer"
```

---

### Task 5: Group-aware table (`RosterAuditTable`)

**Files:**
- Modify: `frontend/src/roster/RosterAuditTable.tsx`
- Test: `frontend/src/roster/RosterAuditTable.test.jsx` (append; existing flat tests must still pass)

**Interfaces:**
- Consumes: `RosterGroup` from `rosterTransform`.
- Produces: `RosterAuditTable` now accepts EITHER `{ players: Player[] }` (flat, unchanged) OR `{ groups: RosterGroup[] }` (grouped). Grouped render emits a labeled heading row per group (label rendered only when non-empty) followed by that group's `RosterAuditRow`s. Row trust cells are unchanged in both modes.

- [ ] **Step 1: Write the failing test**

```jsx
// @vitest-environment jsdom
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RosterAuditTable } from "./RosterAuditTable";

const row = (id, pos) => ({
  player_id: id, full_name: id, position: pos, model_grade: "ACTIVE_B",
  model_status_applies: true, signal_completeness: 0.5, caveats: [],
});

describe("RosterAuditTable grouped", () => {
  it("renders a heading per group and its rows; trust cells preserved", () => {
    const groups = [
      { key: "WR", label: "WR", players: [row("wr1", "WR")] },
      { key: "QB", label: "QB", players: [row("qb1", "QB")] },
    ];
    const { container } = render(<RosterAuditTable groups={groups} />);
    // Assert the GROUP HEADING rows directly (finding E): "WR"/"QB" also appear in the
    // position cell, so getAllByText would false-pass even if headings were never rendered.
    // Querying the heading class proves both that headings exist AND their order/labels (finding C+E).
    const headings = container.querySelectorAll(".dg-roster__group-heading");
    expect([...headings].map((h) => h.textContent)).toEqual(["WR", "QB"]);
    expect(screen.getByText("wr1")).toBeTruthy();
    // per-row trust cell (signal completeness %) still rendered
    expect(screen.getAllByText("50%").length).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/roster/RosterAuditTable.test.jsx`
Expected: FAIL (grouped prop not supported).

- [ ] **Step 3: Write minimal implementation**

```tsx
// frontend/src/roster/RosterAuditTable.tsx
import type { RosterGroup } from "./rosterTransform";
import type { RosterAuditResponse } from "../lib/api";
import { RosterAuditRow } from "./RosterAuditRow";

const COLUMNS = [
  "Player", "Pos", "Team", "Age", "Model grade", "Model status",
  "DVS", "Age signal", "Signal completeness", "Caveats",
];

type Player = NonNullable<RosterAuditResponse["players"]>[number];

export function RosterAuditTable(
  props: { players: Player[] } | { groups: RosterGroup[] },
) {
  const groups: RosterGroup[] =
    "groups" in props ? props.groups : [{ key: "__all__", label: "", players: props.players }];

  return (
    <table className="dg-roster__table">
      <thead>
        <tr>{COLUMNS.map((c) => <th key={c}>{c}</th>)}</tr>
      </thead>
      <tbody>
        {groups.map((g) => (
          <GroupBlock key={g.key} group={g} />
        ))}
      </tbody>
    </table>
  );
}

function GroupBlock({ group }: { group: RosterGroup }) {
  return (
    <>
      {group.label !== "" && (
        <tr className="dg-roster__group-heading">
          <th colSpan={COLUMNS.length} scope="rowgroup">{group.label}</th>
        </tr>
      )}
      {group.players.map((p) => (
        <RosterAuditRow key={p.player_id} player={p} />
      ))}
    </>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- src/roster/RosterAuditTable.test.jsx`
Expected: PASS (existing flat tests + new grouped test).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/roster/RosterAuditTable.tsx frontend/src/roster/RosterAuditTable.test.jsx
git commit -m "feat(roster): Inc3 Task A — group-aware RosterAuditTable"
```

---

### Task 6: Wire controls + transform into the container (`RosterAudit`)

**Files:**
- Modify: `frontend/src/roster/RosterAudit.tsx`
- Modify: `frontend/src/roster/RosterAuditRow.tsx` (add `data-player-id`)
- Test: `frontend/src/roster/RosterAudit.test.jsx` (append new tests; ALSO widen the one existing disclaimer assertion to `getAllByText` per finding A — all other existing tests pass unchanged)

**Interfaces:**
- Consumes: `applyFilter`, `applySort`, `applyGroup`, `RosterAuditControls`, all types.
- Produces: no new export; the container now owns `sortKey/groupBy/positions/prospect` local state, renders `RosterAuditControls`, runs the transform, and renders flat or grouped table. Default state renders backend order unchanged. A non-empty roster filtered to zero rows shows an explicit "filters produced no rows" notice (distinct from the empty-roster `EmptyState`), preserving the header + disclaimer + a reset.

- [ ] **Step 1: Write the failing test**

```jsx
// (append to RosterAudit.test.jsx)
import { fireEvent } from "@testing-library/react";

it("default view preserves backend order (no client re-sort)", async () => {
  mockFetch(200, activeAudit()); // players: [WR p1, QB p2]
  render(<RosterAudit />);
  await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
  const rows = screen.getAllByRole("row").map((r) => r.getAttribute("data-player-id")).filter(Boolean);
  expect(rows).toEqual(["p1", "p2"]);
});

it("filtering to zero rows shows a filters-no-rows notice, not the empty-roster state", async () => {
  mockFetch(200, activeAudit());
  render(<RosterAudit />);
  await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
  // deselect all real positions by toggling a position the roster lacks is not possible;
  // instead choose Prospects-only on an all-active roster -> zero rows
  fireEvent.change(screen.getByLabelText(/players/i), { target: { value: "prospects" } });
  await waitFor(() => expect(screen.getByText(/no rows match the current filters/i)).toBeTruthy());
  // header + controls disclaimers both mounted (intentional D5 double-render, finding A)
  expect(screen.getAllByText(/experimental — not decision-grade/i).length).toBeGreaterThanOrEqual(1);
});
```

**Also update the EXISTING Inc2 assertion (finding A):** in `RosterAudit.test.jsx`, the existing test "renders header + table on 200 active" currently asserts `expect(screen.getByText(/experimental — not decision-grade/i)).toBeTruthy();`. Once controls render, that string appears twice (header + controls). Change that one line to:

```jsx
expect(screen.getAllByText(/experimental — not decision-grade/i).length).toBeGreaterThanOrEqual(1);
```

(Requires `RosterAuditRow` to expose `data-player-id`; add it in Step 3.)

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/roster/RosterAudit.test.jsx`
Expected: FAIL (no controls; no data-player-id; no filters-no-rows notice).

- [ ] **Step 3: Write minimal implementation**

In `frontend/src/roster/RosterAuditRow.tsx`, add `data-player-id={player.player_id}` to the row `<tr>` (alongside the existing `data-applies`/`data-grade` attributes).

Replace the render tail of `frontend/src/roster/RosterAudit.tsx` (from `const { data } = state;` down) with:

```tsx
  const { data } = state;
  const allPlayers = data.players ?? [];
  const cards = data.qb_context_cards ?? [];
  const caveats = data.caveats ?? [];

  return <ReadyView data={data} allPlayers={allPlayers} cards={cards} caveats={caveats} />;
}

function ReadyView({ data, allPlayers, cards, caveats }: {
  data: RosterAuditResponse;
  allPlayers: Player[];
  cards: NonNullable<RosterAuditResponse["qb_context_cards"]>;
  caveats: string[];
}) {
  const [ctrl, setCtrl] = useState<ControlsState>({
    sortKey: "none", groupBy: "none", positions: [], prospect: "all",
  });
  const allPositions = Array.from(new Set(allPlayers.map((p) => p.position)));
  const filtered = applyFilter(allPlayers, { positions: ctrl.positions, prospect: ctrl.prospect });
  const groups = applyGroup(filtered, ctrl.groupBy, ctrl.sortKey);
  const filteredOutCount = allPlayers.length - filtered.length;
  const reset = () => setCtrl({ sortKey: "none", groupBy: "none", positions: [], prospect: "all" });

  return (
    <div className="dg-roster">
      <RosterAuditHeader
        status={data.status}
        modelStatusByPosition={data.model_status_by_position ?? {}}
        caveats={caveats}
        droppedPlayerCount={data.dropped_player_count ?? 0}
      />
      {allPlayers.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          <RosterAuditControls
            {...ctrl}
            allPositions={allPositions}
            filteredOutCount={filteredOutCount}
            onChange={setCtrl}
            onReset={reset}
          />
          {filtered.length === 0 ? (
            <p className="dg-roster__no-match" role="status">
              No rows match the current filters.{" "}
              <button type="button" onClick={reset}>Reset</button>
            </p>
          ) : (
            <RosterAuditTable groups={groups} />
          )}
        </>
      )}
      <QbContextSection cards={cards} />
    </div>
  );
}
```

Add the imports at the top of `RosterAudit.tsx`:

```tsx
import { RosterAuditControls, type ControlsState } from "./RosterAuditControls";
import { applyFilter, applyGroup, type Player } from "./rosterTransform";
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- src/roster/RosterAudit.test.jsx`
Expected: PASS (existing + new container tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/roster/RosterAudit.tsx frontend/src/roster/RosterAudit.test.jsx frontend/src/roster/RosterAuditRow.tsx
git commit -m "feat(roster): Inc3 Task A — wire controls + transform into container"
```

---

### Task 7: Full-gate closeout verification

**Files:** none (verification only; AGENT_SYNC + ledger updates are separate state-doc commits).

- [ ] **Step 1: Run the full FE gate**

Run: `npm --prefix frontend run typecheck && npm --prefix frontend run lint && npm --prefix frontend run test && npm --prefix frontend run build`
Expected: all green; full roster vitest suite (transform + controls + table + container) passes.

- [ ] **Step 2: Confirm banned-language gate clean**

Run: `npm --prefix frontend run banned-language` (the actual gate = `node scripts/check-banned-language.mjs`; also exposed as `test:governance`).
Run: `grep -riE "sell|hold|cut|replace|elite|bust|win|loss|tier" frontend/src/roster/RosterAuditControls.tsx frontend/src/roster/rosterTransform.ts`
Expected: banned-language gate exits 0; grep finds no verdict/action vocabulary in labels/headings.

- [ ] **Step 3: Confirm zero backend/contract drift**

Run: `git diff --name-only origin/main...HEAD`
Expected: only `frontend/src/roster/*` (+ the spec/plan docs); NO `app/`, `src/`, `frontend/openapi.json`, or `frontend/src/lib/api/*.gen.ts` changes.
Run: `.venv/bin/python3.14 -m pytest tests/contract/test_openapi_drift_contract.py -q` (the actual OpenAPI drift guard — Python contract test).
Expected: PASS unchanged (no contract/OpenAPI change).

- [ ] **Step 4: Run the sprint-closeout tollgate**

Run: `.venv/bin/python3.14 scripts/verify_sprint_closeout.py --base origin/main`
Expected: ENFORCE PASS (full Python suite unaffected; FE gate green; standalone-script checks clean).

- [ ] **Step 5: Commit (state docs)**

```bash
git add AGENT_SYNC.md docs/agent-ledger/$(date +%F).md
git commit -m "docs(sync): RA Inc3 Task A build complete — full gate green"
```

---

## Self-Review

**1. Spec coverage:**
- D1 default backend order → Task 1 (`applySort "none"`) + Task 6 (default state) + container test "default view preserves backend order". ✓
- D2 4-sort set incl. opt-in xVAR, null-safe multi-key → Task 1. ✓
- D3 Position + Prospect/Active filters, empty=all, filtered-zero notice, no trust-hide → Task 2 + Task 6. ✓
- D4 opt-in None/Position/Depreciation-band, producer-token Option P, deterministic group order, missing bucket last → Task 3 (+ determinism test). ✓
- D5 trust preservation, de-emphasis styling-only, sticky disclaimer → Task 4 (disclaimer in controls) + Task 5 (row trust cells in groups) + Task 6 (header preserved on filtered-zero). ✓
- D6 sticky toolbar, single active sort, dropdowns, local-state-only → Task 4 + Task 6. ✓
- AC-8 no regression / no backend-contract change / OpenAPI drift untouched → Task 7. ✓

**2. Placeholder scan:** No TBD/TODO; every code step shows complete code. ✓

**3. Type consistency:** `SortKey`/`GroupKey`/`ProspectFilter`/`RosterFilterState`/`RosterGroup`/`ControlsState`/`Player` defined in Task 1–4 and reused verbatim in Tasks 5–6. `applySort`/`applyFilter`/`applyGroup` signatures consistent across tasks. `data-player-id` added in Task 6 Step 3 is consumed by the Task 6 container test. ✓

---

## Governance

- Spec (dual-CLEARED v2, `b641f87`) is the contract for this plan. Build via the cockpit cycle: Codex RED → Claude GREEN → Codex (technical) + Gemini (governance) dual-CLEAR per task → David-authorized commit → zero-divergence audit.
- No backend / contract / model / Engine-A / Engine-B / training / market change. `decision_supported` consumed, never overridden. Read-only Roster Audit HOLD lift covers Inc3; rest of HOLD intact.
- This plan is itself routed through the cockpit for dual-CLEAR before any task execution, then David authorizes proceeding.
