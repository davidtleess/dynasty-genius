import type { RosterAuditResponse } from "../lib/api";
import { inputName } from "../lib/copy";
import { PlayerNameButton } from "../player/playerSelection";
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
//
// DG-110: the card's name opens that quarterback's card. The QB contract does
// not carry a sleeper id, so the container hands down the id it already read
// for the same player on the roster (same payload, same player_id key) — a
// join, never a guess. No id, no link.
//
// ── DG-117: THE DASH WALL ───────────────────────────────────────────────────
//
// All five of David's quarterbacks came back with every metric null, so the
// section rendered fifteen em dashes under three labels and then repeated the
// same two caveats five times each. An em dash beside a label asserts nothing;
// it is an empty column dressed up, and it is the exact thing the honesty law
// forbids. What the payload actually says is not "no data" but something
// specific and sayable: `identity_coverage` is "NONE" on every card, and the
// producer only fetches passing telemetry for a card whose coverage is FULL or
// PARTIAL (roster_auditor.py:596-604). So the numbers are absent because the
// player was never matched to the record they come from — which is what the
// section now says, in one sentence, in place of the dashes.
//
// Nothing is deleted: a card that HAS numbers still prints them, the names stay
// pressable, and every caveat still reaches the screen. Caveats that every card
// carries are said once for all of them rather than once per card, because a
// caveat true of all five is a fact about the data lane, not about a player.

type Card = NonNullable<RosterAuditResponse["qb_context_cards"]>[number];

/** True when the card carries at least one of the three passing readings. */
function hasNumbers(card: Card): boolean {
  return card.epa_per_dropback != null || card.cpoe != null || card.dakota != null;
}

// Why a card has no numbers, read off the field that decides it. Coverage is
// the producer's own gate: FULL/PARTIAL means it went and fetched, anything
// else means it never did (roster_auditor.py:596-604). The two cases are
// genuinely different and a reader deserves the one that is true.
function matched(card: Card): boolean {
  return card.identity_coverage === "FULL" || card.identity_coverage === "PARTIAL";
}

function whyNoNumbers(card: Card): string {
  return matched(card)
    ? "we have his record but no passing numbers in it yet"
    : "we have not matched him to the passing records these come from";
}

function sectionWhyNoNumbers(cards: Card[]): string {
  return cards.every((c) => !matched(c))
    ? "We have not matched any of these quarterbacks to the passing records these numbers come from, so there is nothing to show for them yet."
    : "We have these quarterbacks' records but no passing numbers in them yet, so there is nothing to show for them.";
}

/** Caveat tokens carried by every card — a fact about the lane, not a player. */
function sharedCaveats(cards: Card[]): string[] {
  const first = cards[0];
  if (cards.length < 2 || first === undefined) return [];
  const rest = cards.slice(1);
  return (first.qb_context_caveats ?? []).filter((token) =>
    rest.every((card) => (card.qb_context_caveats ?? []).includes(token)),
  );
}

export function QbContextSection({
  cards,
  sleeperIdByPlayerId = {},
}: {
  cards: NonNullable<RosterAuditResponse["qb_context_cards"]>;
  sleeperIdByPlayerId?: Record<string, string>;
}) {
  const list = cards ?? [];
  if (list.length === 0) return null;
  const noneHaveNumbers = list.every((c) => !hasNumbers(c));
  const shared = sharedCaveats(list);

  return (
    <section className="dg-roster__qb" aria-label="QB context cards">
      <h2>QB context</h2>
      <p className="dg-roster__qb-note">
        How his passing has actually gone — context for reading the roster above, not a
        grade on him.
      </p>
      {noneHaveNumbers && (
        <p className="dg-roster__qb-empty">{sectionWhyNoNumbers(list)}</p>
      )}
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
            {hasNumbers(c) ? (
              <span>
                {" "}
                {inputName("epa_per_dropback")}: {c.epa_per_dropback ?? "—"} ·{" "}
                {inputName("cpoe")}: {c.cpoe ?? "—"} · {inputName("dakota")}:{" "}
                {c.dakota ?? "—"}
              </span>
            ) : noneHaveNumbers ? null : (
              // One card among several is empty: the section sentence above does
              // not apply, so this row carries its own reason rather than a dash.
              <span> — no passing numbers yet, {whyNoNumbers(c)}.</span>
            )}
            <TokenNotes tokens={c.qb_context_annotations ?? []} />
            <TokenNotes
              tokens={(c.qb_context_caveats ?? []).filter((t) => !shared.includes(t))}
            />
          </li>
        ))}
      </ul>
      {shared.length > 0 && (
        <div className="dg-roster__qb-shared">
          <p>True of every quarterback here:</p>
          <TokenNotes tokens={shared} />
        </div>
      )}
    </section>
  );
}
