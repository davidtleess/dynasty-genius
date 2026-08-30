// DG primitive: the receipt — every number can disclose its provenance
// (vision §2). Focusable disclosure control: keyboard (Enter/Escape), touch,
// and click are first-class; hover is never the only path (seed-9 contract).
import { useLayoutEffect, useRef, useState } from "react";
import "./ui.css";

/** Breathing room kept between the panel and either edge of the viewport. */
const EDGE_GUTTER_PX = 8;

export function ReceiptTrigger({
  label,
  capturedAt,
  source,
}: {
  label: string;
  capturedAt: string;
  source: string;
}) {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLSpanElement | null>(null);

  /*
   * DG-117 REVIEW-PANEL FIX — the third place this surface leaked sideways.
   * The panel is anchored to its trigger, and on Daily What-Changed the trigger
   * sits at the right end of a row: at 390px the open panel ran to x=548 in a
   * 390px viewport and took the whole document 158px sideways (measured in
   * Chromium; 167px with all twenty open). It is the first surface in the nav,
   * one tap in. Pre-existing on main, not new here — and inside the defect this
   * ticket exists to close, so it closes here.
   *
   * CSS alone cannot do it: the panel's containing block is the 19px trigger,
   * so no width clamp can know how much room is left to the right of it, and
   * right-anchoring instead would push a left-hand receipt off the other edge,
   * where content is not merely scrolled but unreachable. So measure and shift
   * back inside, never further than the left gutter — the panel always fits and
   * nothing is ever pushed out of reach. The clamp in ui.css keeps it narrower
   * than the viewport in the first place; this keeps it inside.
   */
  useLayoutEffect(() => {
    const panel = panelRef.current;
    if (!open || panel === null) return;

    const place = () => {
      panel.style.transform = "";
      const rect = panel.getBoundingClientRect();
      const viewport = document.documentElement.clientWidth;
      // No layout (jsdom, display:none): nothing measured, nothing moved.
      if (viewport === 0 || rect.width === 0) return;
      const overshoot = rect.right - (viewport - EDGE_GUTTER_PX);
      if (overshoot <= 0) return;
      const room = Math.max(0, rect.left - EDGE_GUTTER_PX);
      panel.style.transform = `translateX(${-Math.min(overshoot, room)}px)`;
    };

    place();
    window.addEventListener("resize", place);
    return () => window.removeEventListener("resize", place);
  }, [open]);

  return (
    <span className="dg-ui-receipt">
      <button
        type="button"
        className="dg-ui-receipt__trigger"
        aria-label={`Provenance for ${label}`}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            setOpen(true);
          }
          if (event.key === "Escape") {
            setOpen(false);
          }
        }}
        onPointerDown={(event) => {
          if (event.pointerType === "touch") {
            setOpen(true);
          }
        }}
      >
        ⌗
      </button>
      {open && (
        <span className="dg-ui-receipt__panel" role="status" ref={panelRef}>
          <span className="dg-ui-receipt__row" data-testid="receipt-raw-source">
            {source}
          </span>
          <span className="dg-ui-receipt__row" data-testid="receipt-raw-captured-at">
            {capturedAt}
          </span>
        </span>
      )}
    </span>
  );
}
