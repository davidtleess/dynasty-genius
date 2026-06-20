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
  { value: "xvar_bracket", label: "xVAR bracket" },
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

export function RosterAuditControls(
  props: ControlsState & {
    allPositions: string[];
    filteredOutCount: number;
    onChange: (next: ControlsState) => void;
    onReset: () => void;
  },
) {
  const {
    sortKey,
    groupBy,
    positions,
    prospect,
    allPositions,
    filteredOutCount,
    onChange,
    onReset,
  } = props;
  const state: ControlsState = { sortKey, groupBy, positions, prospect };

  // positions === [] is the "All" sentinel. Materialize it before toggling so the
  // UI never shows "all included" while every checkbox reads unchecked.
  const togglePos = (pos: string) => {
    const current = positions.length === 0 ? allPositions : positions;
    const next = current.includes(pos)
      ? current.filter((p) => p !== pos)
      : [...current, pos];
    // empty OR full selection both normalize back to the All sentinel ([]),
    // honoring the "empty = All, never blank roster" lock.
    const normalized =
      next.length === 0 || next.length === allPositions.length ? [] : next;
    onChange({ ...state, positions: normalized });
  };

  return (
    <div className="dg-roster__controls">
      <label>
        Sort by
        <select
          value={sortKey}
          onChange={(e) => onChange({ ...state, sortKey: e.target.value as SortKey })}
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Group by
        <select
          value={groupBy}
          onChange={(e) => onChange({ ...state, groupBy: e.target.value as GroupKey })}
        >
          {GROUP_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
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
        <select
          value={prospect}
          onChange={(e) =>
            onChange({ ...state, prospect: e.target.value as ProspectFilter })
          }
        >
          {PROSPECT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
      <span className="dg-roster__controls-disclaimer">
        Experimental — not decision-grade.
      </span>
      {filteredOutCount > 0 && (
        <span className="dg-roster__filtered-note" role="status">
          {filteredOutCount} rows filtered out
          <button type="button" onClick={onReset}>
            Reset
          </button>
        </span>
      )}
    </div>
  );
}
