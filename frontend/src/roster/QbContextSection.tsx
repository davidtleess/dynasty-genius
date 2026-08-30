import type { RosterAuditResponse } from "../lib/api";
import { PlayerNameButton } from "../player/playerSelection";

// QB context cards: supplementary signal only. Rendered verbatim from the contract,
// explicitly labeled context-signal / not-decision-grade. Empty -> nothing.
//
// DG-110: the card's name opens that quarterback's card. The QB contract does
// not carry a sleeper id, so the container hands down the id it already read
// for the same player on the roster (same payload, same player_id key) — a
// join, never a guess. No id, no link.
export function QbContextSection({
  cards,
  sleeperIdByPlayerId = {},
}: {
  cards: NonNullable<RosterAuditResponse["qb_context_cards"]>;
  sleeperIdByPlayerId?: Record<string, string>;
}) {
  const list = cards ?? [];
  if (list.length === 0) return null;
  return (
    <section className="dg-roster__qb" aria-label="QB context cards">
      <h2>QB context</h2>
      <p className="dg-roster__disclaimer">Context signal — not decision-grade.</p>
      <ul>
        {list.map((c) => (
          <li
            key={c.player_id}
            className="dg-roster__qb-card"
            data-coverage={c.identity_coverage}
          >
            <strong>
              <PlayerNameButton
                sleeperId={sleeperIdByPlayerId[c.player_id]}
                name={c.full_name}
                context="QB"
                className="dg-roster__name"
              />
            </strong>
            <span>
              {" "}
              EPA/db {c.epa_per_dropback ?? "—"} · CPOE {c.cpoe ?? "—"} · DAKOTA{" "}
              {c.dakota ?? "—"}
            </span>
            <div>{(c.qb_context_annotations ?? []).join(", ") || "—"}</div>
            <div>{(c.qb_context_caveats ?? []).join(", ") || "—"}</div>
          </li>
        ))}
      </ul>
    </section>
  );
}
