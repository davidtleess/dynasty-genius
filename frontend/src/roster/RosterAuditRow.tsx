// One roster row + an inline expand revealing the full per-player detail. Generated
// types mark most fields optional/nullable, so every array/number is normalized.
//
// DG-109 review fix: Roster Audit is the SECOND item in the primary nav rail and
// it printed 79 raw pipeline keys — `PRE_MODEL`, `no_market_overlay`,
// `approaching_cliff`, `age_within_two_years_of_position_cliff` and the rest —
// on a surface David reaches in one click. Every one of them already had a word
// waiting in the dictionary; this surface was simply never wired to it and never
// mounted by the enforcement test. Both are fixed. The raw grade still rides
// `data-grade` for CSS and tests, exactly as the trust strip keeps its own.
import { useState } from "react";

import type { RosterAuditResponse } from "../lib/api";
import { liquidityWord, valueWord } from "../lib/copy";
import { PlayerNameButton } from "../player/playerSelection";
import { TokenNotes } from "../ui/TokenNotes";

type Player = NonNullable<RosterAuditResponse["players"]>[number];

const num = (v: number | null | undefined) => (v == null ? "—" : String(v));

// DG-110: the NAME opens the player's card — this table lists every player
// David owns and had no route to any of their cards. The inline detail (the
// row's caveats, drivers, risk flags, counter-argument) is truth-bearing and
// stays exactly where it was, behind its own "Details" control — still spoken
// through DG-109's dictionary, never as raw pipeline keys.
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
        <td>{valueWord(player.model_grade)}</td>
        <td>{player.model_status_applies ? "applies" : "n/a"}</td>
        <td>
          {num(player.dynasty_value_score)}
          {player.dvs_pct != null ? ` (${player.dvs_pct}%)` : ""}
        </td>
        <td>
          {ra?.signal ? valueWord(ra.signal) : "—"}
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
            {drivers.length > 0 && (
              <>
                <p>What is driving this:</p>
                <TokenNotes tokens={drivers} />
              </>
            )}
            {risks.length > 0 && (
              <>
                <p>Risks:</p>
                <TokenNotes tokens={risks} />
              </>
            )}
            <p>
              Projections: {num(player.projection_1y)} / {num(player.projection_2y)} /{" "}
              {num(player.projection_3y)}
            </p>
            <p>
              Value over replacement: {num(player.xvar)} · Age-weighted value risk:{" "}
              {num(ra?.biological_debt_score)}
            </p>
            {ra?.liquidity_risk && (
              <p>Trade flexibility: {liquidityWord(ra.liquidity_risk)}</p>
            )}
            <TokenNotes tokens={caveats} />
          </td>
        </tr>
      )}
    </>
  );
}
