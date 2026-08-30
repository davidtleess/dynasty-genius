import type { RosterAuditResponse } from "../lib/api";
import { inputName } from "../lib/copy";
import { TokenNotes } from "../ui/TokenNotes";

// QB context cards: supplementary signal only. Empty -> nothing.
//
// DG-111 REVIEW-PANEL FIX: this surface still stamped "Context signal — not
// decision-grade." out of a <p className="dg-roster__disclaimer">, and David's
// live roster returns five of these cards, so it was on his screen while the
// ticket certified Roster Audit stamp-free. It was the third instance of the
// register on this one surface — the header and the filter bar were retired and
// this one was missed, because the guard pinned five whole strings and this was
// a sixth variant of the same sentence.
//
// The register goes; the fact it stood on does not. `context_role` is the
// literal "context_signal" and `decision_supported` is the literal False
// (roster_audit_models.py QBContextCard), which together mean: these are
// descriptive passing readings shown beside the roster, and nothing here grades
// the quarterback. That is now said in one plain sentence.
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
      <p className="dg-roster__qb-note">
        How his passing has actually gone — context for reading the roster above, not a
        grade on him.
      </p>
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
