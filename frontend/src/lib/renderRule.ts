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
//   [data-receipt]    the "where this comes from" layer. Spec §1 permits the raw
//                     key here and only here — a receipt that renamed the artifact
//                     it cites would stop being a receipt.
//   [data-user-text]  text the league's own people wrote (team names, player
//                     names). "MDEF" is a manager's team name, not our vocabulary,
//                     and a dictionary must not rewrite it.
//
// `title` attributes are the product's existing hover-receipt convention and are
// likewise receipt layer (see copy.ts `receiptDetail`), so they are not audited.

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
const ALLOWED_SHOUTS: ReadonlySet<string> = new Set<string>([]);

const EXEMPT_SUBTREE_SELECTOR = "[data-receipt],[data-user-text]";
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
 * Underscore keys are matched first and then blanked out, so `ENGINE_B` is
 * reported once as the key it is rather than a second time as its shouted
 * halves — one offender, one line to fix.
 */
export function findRawCopy(text: string): string[] {
  const found: string[] = [];
  let remaining = text;
  for (const match of text.matchAll(RAW_KEY_PATTERN)) {
    found.push(match[0]);
    remaining = remaining.replace(match[0], " ".repeat(match[0].length));
  }
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
    .map((f) => `  ${f.token}\n      in: ${f.context}\n      at: ${f.where}`)
    .join("\n");
}
