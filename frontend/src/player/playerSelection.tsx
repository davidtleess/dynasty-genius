// One selection sink for the whole product (DG-110).
//
// DG-089 gave the change feed a working "this is my player, let me click him"
// gesture by threading a handler down through context rather than props.
// DG-110 generalises that: the shell provides the sink ONCE, and every leaf
// that renders a player's name — roster rows, cut candidates, league pools, QB
// context cards, trade lanes, universe chips — opens the same card by reading
// it here. No surface has to be re-plumbed to become reachable again.
//
// Honesty rules baked into PlayerNameButton, carried over from DG-089:
//   * no sink (a bare mount, a test) -> the name renders as plain text; a
//     surface never grows a phantom button that does nothing.
//   * no sleeper id (a blank or whitespace-only one) -> plain text too. The
//     player card is addressed BY sleeper id; a row we cannot open honestly
//     stays unlinked rather than opening an empty card.
import { createContext, type ReactNode, useContext } from "react";
import "./playerSelection.css";

export type SelectPlayer = (sleeperId: string, label: string) => void;

export const PlayerSelectionContext = createContext<SelectPlayer | null>(null);

export function usePlayerSelection(): SelectPlayer | null {
  return useContext(PlayerSelectionContext);
}

export function PlayerSelectionProvider({
  value,
  children,
}: {
  value: SelectPlayer | null;
  children: ReactNode;
}) {
  return (
    <PlayerSelectionContext.Provider value={value}>
      {children}
    </PlayerSelectionContext.Provider>
  );
}

export function PlayerNameButton({
  sleeperId,
  name,
  context,
  className,
  children,
}: {
  /** Sleeper id — the player card's address. Blank/absent => not a link. */
  sleeperId: string | null | undefined;
  name: string;
  /** Extra row context (position, team) folded into the accessible name. */
  context?: string | undefined;
  className?: string | undefined;
  /** Custom label body; defaults to the name text. */
  children?: ReactNode;
}) {
  const selectPlayer = usePlayerSelection();
  // Trim before the truthiness gate: a whitespace-only id is as blank as null.
  const openId = sleeperId?.trim() || null;
  const body = children ?? name;
  if (selectPlayer === null || openId === null) {
    return <>{body}</>;
  }
  // The button's aria-label replaces name-from-content, so carry the row
  // context the label would otherwise swallow for screen-reader users.
  return (
    <button
      type="button"
      className={className ? `dg-player-open ${className}` : "dg-player-open"}
      aria-label={context ? `Open ${name}, ${context}` : `Open ${name}`}
      onClick={() => selectPlayer(openId, name)}
    >
      {body}
    </button>
  );
}
