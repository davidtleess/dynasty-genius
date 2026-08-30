// DG-114 — the player card's open/closed state, and its one history entry.
//
// The spec asks for four ways out of the card (§4.3): the close button, Escape,
// a press on the scrim, and BROWSER BACK. Back is the interesting one, because
// the obvious way to get it — put the player in the URL — is explicitly out of
// scope: `?player=` addressability reverses a recorded deferral (I3-owned) and
// is David's open decision. This ticket flags it; it does not reverse it.
//
// So the card pushes a history entry at the SAME url. Back then pops that entry
// and the card closes, while nothing about the address bar changes and no
// bookmark of an open card is created. Every close path funnels through here,
// and `popstate` is the only place the flag is cleared, so the entry and the
// card can never disagree about whether they are open.
import { useCallback, useEffect, useRef, useState } from "react";

export type SelectedPlayer = { sleeperId: string; label: string };

export type PlayerCardState = {
  player: SelectedPlayer | null;
  open: (sleeperId: string, label: string) => void;
  close: () => void;
  /**
   * Close the card WITHOUT walking history, and report whether its entry is
   * still the top of the stack. The caller is about to write history itself and
   * must replace that entry rather than push past it.
   */
  consumeHistoryEntry: () => boolean;
};

export function usePlayerCard(): PlayerCardState {
  const [player, setPlayer] = useState<SelectedPlayer | null>(null);
  // Whether OUR entry is on top. A ref, not state: the popstate listener has to
  // read the current value, and re-subscribing on every change would drop
  // events between renders.
  const pushedRef = useRef(false);

  const open = useCallback((sleeperId: string, label: string) => {
    setPlayer({ sleeperId, label });
    // Opening a SECOND player from inside the card (a name in the evidence)
    // must not stack a second entry, or one Back would leave the card open on
    // the previous player with no visible reason.
    if (!pushedRef.current) {
      window.history.pushState(
        { dgPlayerCard: true },
        "",
        `${window.location.pathname}${window.location.search}`,
      );
      pushedRef.current = true;
    }
  }, []);

  const close = useCallback(() => {
    setPlayer(null);
    if (pushedRef.current) {
      pushedRef.current = false;
      // Leaves the stack exactly as it was before the card opened, so Back
      // after closing goes where it would have gone without the card at all.
      window.history.back();
    }
  }, []);

  const consumeHistoryEntry = useCallback(() => {
    const wasPushed = pushedRef.current;
    pushedRef.current = false;
    setPlayer(null);
    return wasPushed;
  }, []);

  useEffect(() => {
    function onPopState() {
      if (pushedRef.current) {
        pushedRef.current = false;
        setPlayer(null);
      }
    }
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  return { player, open, close, consumeHistoryEntry };
}
