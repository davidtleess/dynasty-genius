// DG-114 — the player card is a drawer, not a page and not a two-step popover.
//
// Before this ticket a row press opened a NEUTRAL PREVIEW — model status,
// market availability, a caveat count — whose only real action was a button
// labelled "Open full evidence card". The press had already asked for the card;
// the preview was a toll booth in front of it. Spec §3: "the two-step 'row
// popover → Open full evidence card' flow is cut; a row press opens the card
// directly."
//
// Shape (spec §3, §4.4): 640px panel from the right on desktop, full-screen
// sheet on phone with a sticky header. Four ways out, all of them here except
// Back, which lives in usePlayerCard.ts with the history entry it pops.
import { type ReactNode, useEffect, useRef } from "react";

import "./PlayerCardDrawer.css";

const FOCUSABLE =
  'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

export function PlayerCardDrawer({
  onClose,
  children,
}: {
  onClose: () => void;
  children: ReactNode;
}) {
  const panelRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  // Where focus was when the card opened, so closing puts it back on the name
  // that was pressed rather than dumping it at the top of the document.
  const returnFocusRef = useRef<Element | null>(null);

  useEffect(() => {
    returnFocusRef.current = document.activeElement;
    closeRef.current?.focus();
    return () => {
      const previous = returnFocusRef.current;
      if (previous instanceof HTMLElement && document.contains(previous)) {
        previous.focus();
      }
    };
  }, []);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        // This listener is on `document`, so it is the LAST thing a keydown
        // reaches. A layer above the card (the ⌘K palette can open over it)
        // stops the event before it gets here — CommandPalette's Escape branch
        // calls stopPropagation for exactly that reason — so one press closes
        // one layer. stopPropagation here is for anything listening beyond
        // document, and cannot un-run a handler that already fired.
        event.stopPropagation();
        onClose();
        return;
      }
      // A modal that lets Tab walk out behind its own scrim is a modal in
      // appearance only: the reader keeps tabbing and lands on controls they
      // cannot see and cannot reach with a mouse.
      //
      // KNOWN LIMIT, measured: while the palette is open OVER the card, focus
      // is in the palette's input — outside this panel — and forward Tab is not
      // caught by the branches below, so it walks out of both layers. Holding
      // focus here in that state would fight the palette for it. A real layer
      // stack is the fix and is not this ticket's.
      if (event.key !== "Tab") {
        return;
      }
      const panel = panelRef.current;
      if (panel === null) {
        return;
      }
      const stops = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (stops.length === 0) {
        return;
      }
      const first = stops[0] as HTMLElement;
      const last = stops[stops.length - 1] as HTMLElement;
      const active = document.activeElement;
      if (event.shiftKey && (active === first || !panel.contains(active))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div className="dg-player-drawer__layer">
      {/* The scrim is a MOUSE convenience — a second, redundant path to a close
          button that is already in the tab order and already bound to Escape.
          It carries no role and no key handler on purpose: giving it one would
          put a duplicate "close" stop in front of every keyboard reader for no
          capability they do not already have. (Two biome-ignore comments stood
          here for rules that never fired on it — `biome check` reported them as
          `suppressions/unused`, so they were suppressing nothing.) */}
      <div className="dg-player-drawer__scrim" aria-hidden="true" onClick={onClose} />
      <aside
        ref={panelRef}
        className="dg-player-drawer dg-motion-drawer-enter"
        role="dialog"
        aria-modal="true"
        aria-label="Player card"
      >
        <div className="dg-player-drawer__bar">
          <span className="dg-player-drawer__label">Player card</span>
          <button
            ref={closeRef}
            type="button"
            className="dg-player-drawer__close"
            aria-label="Close player card"
            onClick={onClose}
          >
            <span aria-hidden="true">✕</span>
          </button>
        </div>
        <div className="dg-player-drawer__body">{children}</div>
      </aside>
    </div>
  );
}
