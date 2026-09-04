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
import { fieldLabel, liquidityWord, valueWord } from "../lib/copy";
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
  // DG-144 (2026-09-03): one number per player. David: "plus or minus 20,
  // remove it, one number per player." DG-128's range under the value was a
  // per-position, per-basis constant — two sigma of the engine that produced
  // the number, never a figure about the player — and is gone from the screen; the API
  // still ships `dvs_band_low` / `dvs_band_high` and this row does not read
  // them. `dvs_engine` still rides `data-basis` on the value cell — measured
  // (B), draft-capital prior (A) or a blend — the way the grade rides
  // `data-grade`. It is a marker only: David ruled on 2026-09-01 that the
  // number is not greyed by its basis.

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
            // The accessible name CONTAINS the visible word ("Details"), so
            // voice control saying "Details" matches it; open/closed state is
            // carried by aria-expanded, not baked into a label that used to
            // say "Expand" even while the row was already expanded.
            aria-label={`Details for ${player.full_name}`}
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
        {/* DG-117: the "applies" / "n/a" cell is gone — see RosterAuditTable's
            COLUMNS note. `model_status_applies` still rides the row on
            `data-applies`, which is what the trust de-emphasis in
            RosterAudit.css and RosterAuditTable.test.jsx read. */}
        <td className="dg-roster__value" data-basis={player.dvs_engine ?? ""}>
          <span className="dg-roster__score">
            {num(player.dynasty_value_score)}
            {player.dvs_pct != null ? ` (${player.dvs_pct}%)` : ""}
          </span>
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
          <td colSpan={9}>
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
              {fieldLabel("xvar")}: {num(player.xvar)} · Age-weighted value risk:{" "}
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
