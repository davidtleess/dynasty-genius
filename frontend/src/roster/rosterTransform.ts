import type { RosterAuditResponse } from "../lib/api";
import { VALUE_OVER_REPLACEMENT } from "../lib/copy";

export type Player = NonNullable<RosterAuditResponse["players"]>[number];

export type SortKey =
  | "none"
  | "age_cliff_risk"
  | "age"
  | "signal_completeness"
  | "xvar";

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
        return cmp(
          num(a1?.biological_debt_score),
          num(a2?.biological_debt_score),
          "desc",
        );
      }
      default:
        return 0;
    }
  });
  return arr;
}

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

export type GroupKey = "none" | "position" | "depreciation_band" | "xvar_bracket";

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

// Coarse, descriptive display-binning of value over replacement (Task B). Edges
// are NOT model tiers: 0.0 is the only principled boundary — above it a player
// is worth more than a freely available replacement at his position, below it
// less. Non-finite and null/undefined xvar route to the no-figure bucket via
// num(), matching applySort.
//
// DG-117: the three headings spelled the quantity as "xVAR", a fourth name for
// what the row detail beside them calls "Value over replacement". The boundary,
// the ordering and the buckets are unchanged; only the words are. The last
// heading states the absence and nothing more — the row's own Model status cell
// and its Details panel carry WHY that player has no figure, and inventing a
// cause here would be a claim this transform cannot see.
const XVAR_BRACKET_ORDER: {
  token: string;
  label: string;
  test: (x: number) => boolean;
}[] = [
  {
    token: "xvar_positive",
    label: `${VALUE_OVER_REPLACEMENT} 0.0 and above`,
    test: (x) => x >= 0,
  },
  {
    token: "xvar_negative",
    label: `${VALUE_OVER_REPLACEMENT} below 0.0 — worth less than a replacement`,
    test: (x) => x < 0,
  },
];
const XVAR_NOT_MODELED = {
  key: "__xvar_not_modeled__",
  label: `No ${VALUE_OVER_REPLACEMENT.toLowerCase()} figure`,
};

export function applyGroup(
  players: Player[],
  key: GroupKey,
  sortKey: SortKey,
): RosterGroup[] {
  if (key === "none") {
    return [{ key: "__all__", label: "", players: applySort(players, sortKey) }];
  }
  if (key === "position") {
    const order: string[] = [];
    const buckets = new Map<string, Player[]>();
    for (const p of players) {
      const existing = buckets.get(p.position);
      if (existing) {
        existing.push(p);
      } else {
        buckets.set(p.position, [p]);
        order.push(p.position);
      }
    }
    return order.map((pos) => ({
      key: pos,
      label: pos,
      players: applySort(buckets.get(pos) ?? [], sortKey),
    }));
  }
  if (key === "xvar_bracket") {
    const buckets = new Map<string, Player[]>();
    for (const p of players) {
      const x = num(p.xvar); // null for null/undefined AND non-finite
      const token =
        x === null
          ? XVAR_NOT_MODELED.key
          : (XVAR_BRACKET_ORDER.find((b) => b.test(x))?.token ?? XVAR_NOT_MODELED.key);
      const existing = buckets.get(token);
      if (existing) {
        existing.push(p);
      } else {
        buckets.set(token, [p]);
      }
    }
    const groups: RosterGroup[] = [];
    for (const b of XVAR_BRACKET_ORDER) {
      const rows = buckets.get(b.token);
      if (rows) {
        groups.push({
          key: b.token,
          label: b.label,
          players: applySort(rows, sortKey),
        });
      }
    }
    const notModeled = buckets.get(XVAR_NOT_MODELED.key);
    if (notModeled) {
      groups.push({
        key: XVAR_NOT_MODELED.key,
        label: XVAR_NOT_MODELED.label,
        players: applySort(notModeled, sortKey),
      });
    }
    return groups;
  }
  // depreciation_band
  const buckets = new Map<string, Player[]>();
  for (const p of players) {
    const sig = p.roster_audit?.signal ?? null;
    const token = BAND_ORDER.find((b) => b.token === sig)?.token ?? MISSING_BAND.key;
    const existing = buckets.get(token);
    if (existing) {
      existing.push(p);
    } else {
      buckets.set(token, [p]);
    }
  }
  const groups: RosterGroup[] = [];
  for (const b of BAND_ORDER) {
    const rows = buckets.get(b.token);
    if (rows) {
      groups.push({ key: b.token, label: b.label, players: applySort(rows, sortKey) });
    }
  }
  const missing = buckets.get(MISSING_BAND.key);
  if (missing) {
    groups.push({
      key: MISSING_BAND.key,
      label: MISSING_BAND.label,
      players: applySort(missing, sortKey),
    });
  }
  return groups;
}
