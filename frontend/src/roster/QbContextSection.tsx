import type { RosterAuditResponse } from "../lib/api";

// QB context cards: supplementary signal only. Rendered verbatim from the contract,
// explicitly labeled context-signal / not-decision-grade. Empty -> nothing.
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
