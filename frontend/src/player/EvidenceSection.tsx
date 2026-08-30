// Evidence body. Renders the FULL steel-manned counter-argument (no
// truncation), top drivers, risk flags (constitutional age-cliff flags amber),
// and caveats.
//
// DG-111 — absence renders nothing. Four "No X available" rows plus an
// "Experimental" badge used to fill this section on a thin player; none of them
// was a fact about him, only a fact about our tables. They are gone.
//
// The one thing absence must NOT do is imply a clean bill of health: an empty
// risk list is "we have no risk notes", never "he has no risks". So when the
// whole block comes back empty, the section says that in one sentence rather
// than rendering an innocent-looking blank.
import type { z } from "zod";

import type { zPlayerDetailResponse } from "../lib/api/zod.gen";

type Evidence = NonNullable<z.infer<typeof zPlayerDetailResponse>["evidence"]>;

function isAgeCliffFlag(text: string): boolean {
  return text.toLowerCase().includes("cliff");
}

function EvidenceBody({ evidence }: { evidence: Evidence }) {
  const counterArgument = evidence.counter_argument;
  const drivers = evidence.top_drivers.items;
  const riskFlags = evidence.risk_flags.items;
  const caveats = evidence.caveats.items;

  const hasCounter = counterArgument.status === "available" && !!counterArgument.text;
  const empty =
    !hasCounter &&
    drivers.length === 0 &&
    riskFlags.length === 0 &&
    caveats.length === 0;

  if (empty) {
    return (
      <p className="dg-evidence__empty">
        We don't have evidence notes on this player yet — that means nothing is written
        down, not that there is nothing to say.
      </p>
    );
  }

  return (
    <>
      {hasCounter && <p className="dg-evidence__counter">{counterArgument.text}</p>}

      {drivers.length > 0 && (
        <ul className="dg-evidence__drivers">
          {drivers.map((driver) => (
            <li key={driver}>{driver}</li>
          ))}
        </ul>
      )}

      {riskFlags.length > 0 && (
        <ul className="dg-evidence__risks">
          {riskFlags.map((flag) => (
            <li
              key={flag}
              className={
                isAgeCliffFlag(flag)
                  ? "dg-evidence__risk dg-evidence__risk--age-cliff-amber"
                  : "dg-evidence__risk"
              }
            >
              {flag}
            </li>
          ))}
        </ul>
      )}

      {caveats.length > 0 && (
        <ul className="dg-evidence__caveats">
          {caveats.map((caveat) => (
            <li key={caveat}>{caveat}</li>
          ))}
        </ul>
      )}
    </>
  );
}

export function EvidenceSection({ evidence }: { evidence: Evidence | null }) {
  return (
    <section className="dg-evidence" aria-label="Evidence">
      {evidence ? (
        <EvidenceBody evidence={evidence} />
      ) : (
        <p className="dg-evidence__empty">Evidence unavailable</p>
      )}
    </section>
  );
}
