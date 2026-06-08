// Surface-3 T8 — evidence body. Renders the FULL steel-manned counter-argument
// (no truncation), top drivers, risk flags (constitutional age-cliff flags amber),
// and caveats. Per-element honest degradation: a missing element renders an
// explicit Experimental / no-data state, never fabricated text.
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

  return (
    <>
      {counterArgument.status === "available" && counterArgument.text ? (
        <p className="dg-evidence__counter">{counterArgument.text}</p>
      ) : (
        <div className="dg-evidence__counter dg-evidence__counter--degraded">
          <p>No counter-argument available</p>
          <span className="dg-evidence__experimental">Experimental</span>
        </div>
      )}

      {drivers.length > 0 ? (
        <ul className="dg-evidence__drivers">
          {drivers.map((driver) => (
            <li key={driver}>{driver}</li>
          ))}
        </ul>
      ) : (
        <p className="dg-evidence__empty">No top drivers available</p>
      )}

      {riskFlags.length > 0 ? (
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
      ) : (
        <p className="dg-evidence__empty">No risk flags available</p>
      )}

      {caveats.length > 0 ? (
        <ul className="dg-evidence__caveats">
          {caveats.map((caveat) => (
            <li key={caveat}>{caveat}</li>
          ))}
        </ul>
      ) : (
        <p className="dg-evidence__empty">No caveats available</p>
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
