import type { RosterAuditResponse } from "../lib/api";
import { inputName } from "../lib/copy";
import { TokenNotes } from "../ui/TokenNotes";

// QB context cards: supplementary signal only. Explicitly labeled
// context-signal / not-decision-grade. Empty -> nothing.
//
// DG-109: the three metrics were labelled `EPA/db`, `CPOE` and `DAKOTA`, and the
// annotation/caveat lists printed their raw tokens. `DAKOTA` was the only one the
// render rule could even see (six capitals); the rest are the data-science
// register regardless. Every number is unchanged.
export function QbContextSection({
  cards,
}: {
  cards: NonNullable<RosterAuditResponse["qb_context_cards"]>;
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
            <strong>{c.full_name}</strong>
            <span>
              {" "}
              {inputName("epa_per_dropback")}: {c.epa_per_dropback ?? "—"} ·{" "}
              {inputName("cpoe")}: {c.cpoe ?? "—"} · {inputName("dakota")}:{" "}
              {c.dakota ?? "—"}
            </span>
            <TokenNotes tokens={c.qb_context_annotations ?? []} />
            <TokenNotes tokens={c.qb_context_caveats ?? []} />
          </li>
        ))}
      </ul>
    </section>
  );
}
