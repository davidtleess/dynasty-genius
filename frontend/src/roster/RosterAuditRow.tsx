import { useState } from "react";
import type { RosterAuditResponse } from "../lib/api";

type Player = NonNullable<RosterAuditResponse["players"]>[number];

const num = (v: number | null | undefined) => (v == null ? "—" : String(v));

// One roster row + an inline expand revealing the full per-player detail. Generated
// types mark most fields optional/nullable, so every array/number is normalized.
export function RosterAuditRow({ player }: { player: Player }) {
  const [open, setOpen] = useState(false);
  const ra = player.roster_audit;
  const caveats = player.caveats ?? [];
  const drivers = player.top_drivers?.items ?? [];
  const risks = player.risk_flags?.items ?? [];

  return (
    <>
      <tr
        data-applies={String(player.model_status_applies ?? false)}
        data-grade={player.model_grade}
      >
        <td>
          <button
            type="button"
            aria-label={`Expand ${player.full_name}`}
            onClick={() => setOpen((o) => !o)}
          >
            {player.full_name}
          </button>
        </td>
        <td>{player.position}</td>
        <td>{player.nfl_team ?? "—"}</td>
        <td>{num(player.age)}</td>
        <td>{player.model_grade}</td>
        <td>{player.model_status_applies ? "applies" : "n/a"}</td>
        <td>
          {num(player.dynasty_value_score)}
          {player.dvs_pct != null ? ` (${player.dvs_pct}%)` : ""}
        </td>
        <td>
          {ra?.signal ?? "—"}
          {ra?.years_to_cliff != null ? ` (${ra.years_to_cliff}y)` : ""}
        </td>
        <td>{Math.round((player.signal_completeness ?? 0) * 100)}%</td>
        <td>{caveats.length}</td>
      </tr>
      {open && (
        <tr className="dg-roster__detail">
          <td colSpan={10}>
            {player.counter_argument?.text && (
              <p>Counter-argument: {player.counter_argument.text}</p>
            )}
            <p>Top drivers: {drivers.join(", ") || "—"}</p>
            <p>Risk flags: {risks.join(", ") || "—"}</p>
            <p>
              Projections: {num(player.projection_1y)} / {num(player.projection_2y)} /{" "}
              {num(player.projection_3y)}
            </p>
            <p>
              xVAR: {num(player.xvar)} · Liquidity: {ra?.liquidity_risk ?? "—"} ·
              Bio-debt: {num(ra?.biological_debt_score)}
            </p>
            <ul>
              {caveats.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </td>
        </tr>
      )}
    </>
  );
}
