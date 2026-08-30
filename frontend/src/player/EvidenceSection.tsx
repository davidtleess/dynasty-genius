// Surface-3 T8 — evidence body. Renders the FULL steel-manned counter-argument
// (no truncation), top drivers, risk flags and caveats — every one of them
// through the copy dictionary, so a snake_case driver never reaches the screen.
//
// DG-109, David's prose ruling: ABSENCE RENDERS NOTHING. "No counter-argument
// available", "No top drivers available", "No risk flags available" and "No
// caveats available" asserted nothing about the player — they were the shape of
// the data showing through. They are gone. What is NOT absence still speaks: a
// caveat we hold is still printed, and a token the dictionary cannot yet say is
// printed raw in the receipt layer rather than dropped.
//
// TWO CORRECTIONS FROM THE DG-109 REVIEW PANEL:
//
// 1. The unmapped fallback used to bolt `data-receipt` onto the risk BULLET
//    itself and print the raw key there. That is body copy wearing a receipt
//    attribute, and because the render-rule audit honours the attribute
//    (renderRule.ts:121), it also meant the enforcement test could never fail on
//    an unmapped risk flag — the one failure it exists to catch. Worse, the
//    token it was hiding is real and common: `age_past_position_cliff` is 14 of
//    17 driver/risk occurrences in a 179-player live sample. Unmapped risk flags
//    now go where drivers and caveats already go, a labelled receipt paragraph
//    of their own, and the dictionary carries the sentence.
//
// 2. WITHHELD IS NOT ABSENT. When a counter-argument or an evidence list carries
//    banned language the backend blanks it and records that in the FIELD's own
//    caveats (`evidence_suppressed_banned_term`, players.py:220-236). Nothing
//    read those arrays, so a suppressed card fell through the `hasContent` gate
//    and rendered as silence — visually identical to a player with no evidence.
//    The per-field caveats are now read, so the withholding speaks.
import type { z } from "zod";

import type { zPlayerDetailResponse } from "../lib/api/zod.gen";
import { lookupToken } from "../lib/copy";
import { TokenNotes } from "../ui/TokenNotes";

type Evidence = NonNullable<z.infer<typeof zPlayerDetailResponse>["evidence"]>;

function isAgeCliffFlag(text: string): boolean {
  return text.toLowerCase().includes("cliff");
}

/**
 * Every per-field caveat on the evidence block, de-duplicated. These are the
 * backend's notes ABOUT a field (chiefly "some notes were withheld"), distinct
 * from the player-level caveat list.
 */
function fieldCaveats(evidence: Evidence): string[] {
  const all = [
    ...(evidence.counter_argument.caveats ?? []),
    ...(evidence.top_drivers.caveats ?? []),
    ...(evidence.risk_flags.caveats ?? []),
    ...(evidence.caveats.caveats ?? []),
  ];
  // `counter_argument_unavailable` is ABSENCE — no counter-argument was written
  // for him — so it stays silent under the absence rule. Suppression does not.
  return Array.from(new Set(all)).filter(
    (token) => token !== "counter_argument_unavailable",
  );
}

function EvidenceBody({ evidence }: { evidence: Evidence }) {
  const counterArgument = evidence.counter_argument;
  const drivers = evidence.top_drivers.items;
  const caveats = evidence.caveats.items;

  const riskNotes = evidence.risk_flags.items.map(lookupToken);
  const spokenRisks = riskNotes.filter((note) => note.mapped);
  const rawRisks = riskNotes.filter((note) => !note.mapped);

  return (
    <>
      {counterArgument.status === "available" && counterArgument.text ? (
        <p className="dg-evidence__counter">{counterArgument.text}</p>
      ) : null}

      <TokenNotes className="dg-evidence__drivers" tokens={drivers} />

      {spokenRisks.length > 0 && (
        <ul className="dg-evidence__risks">
          {spokenRisks.map((note) => (
            // The amber age-cliff treatment is constitutional, so it keys off
            // the RAW token — the sentence says "decline", not "cliff".
            <li
              key={note.raw}
              className={
                isAgeCliffFlag(note.raw)
                  ? "dg-evidence__risk dg-evidence__risk--age-cliff-amber"
                  : "dg-evidence__risk"
              }
            >
              {note.text}
            </li>
          ))}
        </ul>
      )}
      {rawRisks.length > 0 && (
        <p
          className="dg-ui-raw-note"
          data-receipt
          data-testid="untranslated-risk-flags"
        >
          Straight from the data feed, not yet written in plain language:{" "}
          {rawRisks.map((note) => note.raw).join(", ")}
        </p>
      )}

      <TokenNotes className="dg-evidence__caveats" tokens={caveats} />
      <TokenNotes
        className="dg-evidence__field-caveats"
        tokens={fieldCaveats(evidence)}
      />
    </>
  );
}

export function EvidenceSection({ evidence }: { evidence: Evidence | null }) {
  // No evidence block at all is absence too — the section itself disappears
  // rather than announcing an empty region.
  if (!evidence) return null;

  const hasContent =
    (evidence.counter_argument.status === "available" &&
      Boolean(evidence.counter_argument.text)) ||
    evidence.top_drivers.items.length > 0 ||
    evidence.risk_flags.items.length > 0 ||
    evidence.caveats.items.length > 0 ||
    // A card whose evidence was WITHHELD has no items and must still speak.
    fieldCaveats(evidence).length > 0;
  if (!hasContent) return null;

  return (
    <section className="dg-evidence" aria-label="Evidence">
      <EvidenceBody evidence={evidence} />
    </section>
  );
}
