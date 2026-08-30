import type { ReactNode } from "react";

import "./ui.css";

// DG-117 — a wide table scrolls inside itself, or it does not scroll at all.
//
// THE DEFECT THIS EXISTS FOR. Measured on the built bundle in Chromium at a
// 390px viewport, 2026-08-30: Roster Audit's table is 559px wide inside a 358px
// column and Model Trust's fold table is 1039px inside the same 358px, and
// neither column clipped or scrolled. So the OVERFLOW went to the page: the
// document's own scrollWidth reached 575px and 1055px against a 390px client
// width — 185px and 665px of sideways scroll. What that costs a reader is not
// the scrollbar; it is that every other element on the surface is laid out
// against a 390px viewport and then stranded beside several hundred pixels of
// empty canvas, so the whole page reads broken to get at one table.
//
// The fix is one rule and one wrapper. The wrapper takes the overflow
// (`overflow-x: auto` in ui.css) and the page keeps its width. Nothing about
// the table changes: the same columns, the same numbers, the same order. A
// table that fits is unaffected — `auto` shows no scrollbar and the wrapper
// is a plain block.
//
// WHY IT IS FOCUSABLE. A scroll container reachable only by dragging is a
// region a keyboard user cannot read, and axe says so (scrollable-region-
// focusable). `tabIndex=0` puts it in the tab order. A named `<section>` is a
// region by element rather than by ARIA attribute, so the reader who tabs in is
// told what they landed in instead of an anonymous group — the name is required
// for exactly that reason, and an unnamed region is worse than none.
export function TableScroll({
  label,
  children,
}: {
  /** What this table is, for the reader who tabs into it. */
  label: string;
  children: ReactNode;
}) {
  return (
    <section
      className="dg-table-scroll"
      // biome-ignore lint/a11y/noNoninteractiveTabindex: a scrollable region must be keyboard-reachable (axe scrollable-region-focusable); the name makes it a landmark to land in, not a control.
      tabIndex={0}
      aria-label={label}
    >
      {children}
    </section>
  );
}
