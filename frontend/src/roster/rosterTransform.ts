import type { RosterAuditResponse } from "../lib/api";

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
