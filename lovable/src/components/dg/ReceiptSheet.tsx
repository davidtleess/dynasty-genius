// DG-203 — the receipt: what our number means, in the producer's own words.
//
// The imported version rendered a per-player driver list the source invented. The accepted bundle
// carries no per-player causal account, so this states the basis that genuinely applies to every
// player, plus whatever this player's own row actually says about what is missing. Nothing here
// explains WHY we and the market disagree, because nothing in the source knows.
//
// The long producer notes sit inside a disclosure. They are true and worth having one press away,
// but a wall of them under every player is the "data-science console" register the product moved off.
import { savedDate } from "@/lib/dg/polish";
import type { BoardRow, DgBundle } from "@/lib/dg/backend";

export function ReceiptSheet({
  row,
  basis,
  snapshot,
}: {
  row: BoardRow;
  basis: DgBundle["basis"];
  snapshot: DgBundle["snapshot"];
}) {
  return (
    <section className="mt-5 rounded-md border p-4" style={{ borderColor: "var(--hairline)" }}>
      <h3 className="text-[13px] font-semibold tracking-tight">Where these numbers come from</h3>

      <p className="mt-2 text-[13px]" style={{ color: "var(--foreground)" }}>
        A rank difference is a reason to look, not proof the market is wrong. Our points and the
        market price are different units and are never subtracted.
      </p>

      {row.missing_reason ? (
        <p className="mt-2 text-[13px]" style={{ color: "var(--foreground)" }}>
          {row.missing_reason}
        </p>
      ) : null}

      <details className="mt-3">
        <summary className="label-caps cursor-pointer" style={{ minHeight: 44 }}>
          What our number counts
        </summary>
        <dl className="mt-2 space-y-2 text-[13px] text-[var(--ink-dim)]">
          <Line term="Our reading">{basis.summary}</Line>
          <Line term="Scoring">{basis.scoring_note}</Line>
          <Line term="The market price">{basis.market_proxy_note}</Line>
          {row.reference_player ? (
            <Line term="Replacement reference">{row.reference_player}</Line>
          ) : null}
          {row.forecast_note ? <Line term="This player">{row.forecast_note}</Line> : null}
        </dl>
      </details>

      <p className="label-caps mt-4" style={{ color: "var(--ink-faint)" }}>
        Saved snapshot · our values {savedDate(snapshot.forecast_date)} · market prices{" "}
        {savedDate(snapshot.market_as_of)} · ownership {savedDate(snapshot.ownership_as_of)}
      </p>
    </section>
  );
}

function Line({ term, children }: { term: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="label-caps">{term}</dt>
      <dd className="mt-0.5" style={{ color: "var(--foreground)" }}>
        {children}
      </dd>
    </div>
  );
}
