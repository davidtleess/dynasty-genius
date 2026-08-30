import { useState } from "react";
import type { RosterAuditResponse } from "../lib/api";
import { PlayerNameButton } from "../player/playerSelection";

type Player = NonNullable<RosterAuditResponse["players"]>[number];

const num = (v: number | null | undefined) => (v == null ? "—" : String(v));

// One roster row + an inline expand revealing the full per-player detail. Generated
// types mark most fields optional/nullable, so every array/number is normalized.
//
// DG-110: the NAME opens the player's card — this table lists every player
// David owns and had no route to any of their cards. The inline detail (the
// row's caveats, drivers, risk flags, counter-argument) is truth-bearing and
// stays exactly where it was, behind its own "Details" control.
export function RosterAuditRow({ player }: { player: Player }) {
  const [open, setOpen] = useState(false);
  const ra = player.roster_audit;
  const caveats = player.caveats ?? [];
  const drivers = player.top_drivers?.items ?? [];
  const risks = player.risk_flags?.items ?? [];

  return (
    <>
      <tr
        data-player-id={player.player_id}
        data-applies={String(player.model_status_applies ?? false)}
        data-grade={player.model_grade}
      >
        <td>
          {/* The card is addressed by sleeper id; a row without one stays
              plain text rather than opening an empty card. */}
          <PlayerNameButton
            sleeperId={player.sleeper_id}
            name={player.full_name}
            context={[player.position, player.nfl_team].filter(Boolean).join(" ")}
            className="dg-roster__name"
          />{" "}
          <button
            type="button"
            className="dg-roster__expand"
            aria-label={`Expand ${player.full_name}`}
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
          >
            Details
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
