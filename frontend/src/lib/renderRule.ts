// DG-109 — THE RENDER RULE.
//
// David's 2026-08-29 ruling: the front end speaks "prose and layman's language …
// Not a data science, data engineering visualization." The Studio spec turns that
// into one mechanical requirement (DG091-STUDIO-SPEC.md §1): **no string
// containing an underscore or an ALL_CAPS token may reach the DOM.**
//
// This module is the enforcement half of the copy dictionary. `copy.ts` holds the
// strings; this holds the rule that proves no component bypassed them. It is
// consumed by renderRule.test.tsx, which mounts the real surfaces against real
// captured payloads and fails if a single raw pipeline key survives to the screen.
//
// WHAT COUNTS AS "REACHING THE DOM"
// The audit reads what a person reads or hears: visible text nodes plus the
// attributes assistive tech speaks (aria-label, alt, placeholder). Two subtrees
// are exempt, and the exemption is a DECLARATION a component has to make, never a
// silent default:
//
//   [data-identifier] an ADDRESS: a file path, an artifact or run id, a hash, a
//                     git sha, a schema version, a lookup key. Rewording an
//                     address destroys the thing it names, so these bytes are
//                     reproduced exactly and the rule stands aside for them.
//   [data-user-text]  text the league's own people wrote (team names, player
//                     names). "MDEF" is a manager's team name, not our vocabulary,
//                     and a dictionary must not rewrite it.
//   [data-quoted]     a document this product CITES, reproduced word for word —
//                     the model card's own text, the backtest artifact's own
//                     column vocabulary. Paraphrasing a quotation misquotes its
//                     source. The narrowest of the three, and it carries a
//                     condition: the source must be NAMED on screen beside it,
//                     so a reader knows whose words they are reading. Two uses
//                     in the product (ModelCardEssentials, FoldTable) and a
//                     third needs that argument in hand.
//
// `title` attributes are the product's existing hover-receipt convention and are
// likewise receipt layer (see copy.ts `receiptDetail`), so they are not audited.
//
// DG-120 — WHY `[data-receipt]` IS NO LONGER ONE OF THEM
// It used to be, and the exemption was doing double duty. A receipt naming
// `run_pvo_refresh.py` is real provenance a person may want to copy; that was
// the argument, and it is still right. But "this subtree is a receipt" and
// "these bytes are an address" are different claims, and skipping the whole
// subtree granted the second on the strength of the first. Unreadable STATUS
// MESSAGES rode in underneath it. Measured on the live product, 2026-08-30, one
// click behind the header pill "Attention — details inside":
//
//     roster_capacity: live_precondition_not_ok:capture_health_ok=degraded
//     2 of 3 stores degraded — model_forward_capture: missing 1 of 67 days (…)
//     adapter_status:ok        mtime_fresh        core_substrate
//
// None of those is an address. Nothing in the product is reachable by
// `live_precondition_not_ok`; it is a sentence someone declined to write, and a
// rule built to catch exactly that shape was blind to it by construction.
//
// So the split is now the one that was always meant: IDENTIFIERS stay raw and
// copyable, MESSAGES go through the dictionary like every other sentence. A
// component can no longer buy silence by calling itself a receipt — it has to
// point at the exact bytes that are an address. `[data-receipt]` remains as the
// LAYER marker (it is what the health card's provenance rows are, and what
// styling and the browser gate read), and it grants nothing.

/** A pipeline key: word characters joined by underscores, in any case. */
const RAW_KEY_PATTERN = /[A-Za-z0-9]+(?:_[A-Za-z0-9]+)+/g;

/**
 * A shouted token: four or more consecutive capitals standing alone. Four is the
 * floor because every acronym this product legitimately speaks is shorter —
 * position codes (QB, RB, WR, TE, DEF, ATH), team codes (NYG, SF), PPG, NFL, IR.
 * `REBUILDING`, `PRE_MODEL`, `EXPERIMENTAL` and `DIVERGENCE_MARKET_HIGH` are not.
 */
const SHOUTED_TOKEN_PATTERN = /(?<![A-Za-z])[A-Z]{4,}(?![A-Za-z])/g;

/**
 * Shouted words the product is allowed to say. Deliberately tiny: an entry here
 * is a claim that a manager reads the word as English, not as machinery. Add one
 * only with that argument in hand — the dictionary is the answer to everything
 * else.
 */
const ALLOWED_SHOUTS: ReadonlySet<string> = new Set<string>([
  // A manager reads this as a year, not as a column name. It appears in the
  // model card's own account of why fold-to-fold error widens around 2020.
  "COVID",
]);

/**
 * DG-117 — THE JARGON LIST.
 *
 * The two patterns above catch machinery by its SHAPE: an underscore, or a
 * shout. A term that is neither still reads as machinery, and the 2026-08-30
 * closeout audit found the proof — `xVAR` survived the whole copy dictionary
 * because it is four characters with only three capitals, so the shout floor
 * (four) never saw it. It then acquired THREE different names on screen for one
 * quantity: "Value above replacement (xVAR)", "xVAR bracket", bare "xVAR", and
 * "Value over replacement" — a manager cannot know those are the same number.
 *
 * So shape is not enough: a term whose only defence is that it looks like a
 * word needs naming outright. Each entry is a claim that the product has ONE
 * agreed name for the thing, held in `copy.ts`, and that this spelling is not
 * it. Adding an entry without adding the replacement to the dictionary is how
 * the drift starts again.
 *
 * Matched case-insensitively and only as a whole word, so a player named
 * "Xavier" and a receipt citing `asset_xvar` (already caught as a raw key) are
 * unaffected. A declared identifier keeps its exemption: `[data-identifier]`
 * may cite the artifact's own vocabulary, because an address that was renamed
 * would stop being an address.
 */
const JARGON_TERMS: readonly { term: string; use: string }[] = [
  // copy.ts VALUE_OVER_REPLACEMENT is the one name.
  { term: "xVAR", use: "Value over replacement" },
];

// The trailing `s?` catches the plural. A term this rule exists to stop drifts
// first by being pluralised — "the xVARs on this roster" — and a word-boundary
// rule that rejects any suffix would have walked straight past it (panel
// finding, verified: `findRawCopy("xVARs")` returned nothing).
const JARGON_PATTERN = new RegExp(
  `(?<![A-Za-z0-9])(?:${JARGON_TERMS.map((j) => j.term).join("|")})s?(?![A-Za-z0-9])`,
  "gi",
);

/** What the dictionary calls a jargon term, for the failure message. */
export function jargonReplacement(token: string): string | undefined {
  const lower = token.toLowerCase();
  const singular = lower.replace(/s$/, "");
  return JARGON_TERMS.find(
    (j) => j.term.toLowerCase() === lower || j.term.toLowerCase() === singular,
  )?.use;
}

/**
 * The three declarations that stand the rule down, and nothing else. Kept as
 * one exported constant so the browser gate (e2e/visual-smoke.spec.ts) reads
 * the same list rather than restating it — the two audits cannot drift about
 * what is exempt.
 */
export const EXEMPT_SUBTREE_SELECTOR =
  "[data-identifier],[data-user-text],[data-quoted]";
const SKIPPED_TAGS: ReadonlySet<string> = new Set(["SCRIPT", "STYLE", "TEMPLATE"]);
const AUDITED_ATTRIBUTES = ["aria-label", "alt", "placeholder"] as const;

export type RawCopyFinding = {
  /** The offending token exactly as it reached the DOM. */
  token: string;
  /** The whole string it sat inside, so the failure names a fixable call site. */
  context: string;
  /** A readable path to the node that rendered it. */
  where: string;
};

/**
 * Every raw token inside one string. Empty array means the string is clean.
 *
 * ONE OFFENDER, ONE LINE TO FIX. The three passes run most-specific first and
 * blank out what they claim, so a token is reported once by the pass that has
 * the most to say about it: `ENGINE_B` is the key it is, not a second time as
 * its shouted halves, and `XVAR` is jargon with a named replacement, not a
 * bare shout the author has to go and look up.
 */
export function findRawCopy(text: string): string[] {
  const found: string[] = [];
  let remaining = text;
  // Blanked AT THE MATCH, not by value: `remaining.replace(match, …)` blanks the
  // first occurrence of that substring, which is a different one whenever an
  // earlier occurrence was skipped by the lookarounds — and the real offender
  // then survived into the next pass and was reported twice ("2XVAR and XVAR"
  // gave ["XVAR","XVAR"]). Every pass runs over a string of the same length
  // with positions preserved, so an index from one is valid in the next.
  const claim = (match: string, index: number): void => {
    found.push(match);
    remaining =
      remaining.slice(0, index) +
      " ".repeat(match.length) +
      remaining.slice(index + match.length);
  };
  for (const match of text.matchAll(RAW_KEY_PATTERN)) claim(match[0], match.index ?? 0);
  for (const match of [...remaining.matchAll(JARGON_PATTERN)])
    claim(match[0], match.index ?? 0);
  for (const match of remaining.matchAll(SHOUTED_TOKEN_PATTERN)) {
    if (!ALLOWED_SHOUTS.has(match[0])) {
      found.push(match[0]);
    }
  }
  return found;
}

function nodePath(element: Element): string {
  const parts: string[] = [];
  let current: Element | null = element;
  while (current && parts.length < 4) {
    const className =
      typeof current.className === "string" && current.className.trim() !== ""
        ? `.${current.className.trim().split(/\s+/).join(".")}`
        : "";
    parts.unshift(`${current.tagName.toLowerCase()}${className}`);
    current = current.parentElement;
  }
  return parts.join(" > ");
}

function record(
  findings: RawCopyFinding[],
  owner: Element,
  text: string,
  label: string,
): void {
  for (const token of findRawCopy(text)) {
    findings.push({
      token,
      context: text.trim().slice(0, 160),
      where: `${nodePath(owner)}${label}`,
    });
  }
}

/**
 * Walk a rendered subtree and report every raw pipeline key that reached a
 * person. An empty array is the passing state.
 */
export function auditRenderedCopy(root: Element): RawCopyFinding[] {
  const findings: RawCopyFinding[] = [];

  const visit = (element: Element): void => {
    if (SKIPPED_TAGS.has(element.tagName)) return;
    if (element.matches(EXEMPT_SUBTREE_SELECTOR)) return;

    for (const attribute of AUDITED_ATTRIBUTES) {
      const value = element.getAttribute(attribute);
      if (value !== null && value !== "") {
        record(findings, element, value, ` [${attribute}]`);
      }
    }

    for (const child of Array.from(element.childNodes)) {
      if (child.nodeType === 3 /* Node.TEXT_NODE */) {
        const text = child.textContent ?? "";
        if (text.trim() !== "") record(findings, element, text, "");
      } else if (child.nodeType === 1 /* Node.ELEMENT_NODE */) {
        visit(child as Element);
      }
    }
  };

  visit(root);
  return findings;
}

/** One readable block naming every finding — the failure message of the rule. */
export function formatRawCopyFindings(findings: RawCopyFinding[]): string {
  if (findings.length === 0) return "no raw copy";
  return findings
    .map((f) => {
      const use = jargonReplacement(f.token);
      const fix = use === undefined ? "" : `\n      say: ${use}`;
      return `  ${f.token}${fix}\n      in: ${f.context}\n      at: ${f.where}`;
    })
    .join("\n");
}
