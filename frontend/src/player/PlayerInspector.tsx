// Surface-3 T6 — MINIMAL player inspector placeholder.
//
// Neutral preview: identity (name + sleeper id) + an "Open full evidence card"
// action only — no grade/edge/delta/recommendation. T7 completes this into the
// full neutral preview (status, presence counts, explicit unmodeled labels).
export function PlayerInspector({
  player,
  onClose,
}: {
  player: { sleeperId: string; label: string };
  onClose: () => void;
}) {
  return (
    <div className="dg-player-inspector">
      <p className="dg-player-inspector__name">{player.label}</p>
      <p className="dg-player-inspector__id">{player.sleeperId}</p>
      <button type="button" className="dg-player-inspector__open">
        Open full evidence card
      </button>
      <button
        type="button"
        className="dg-player-inspector__close"
        aria-label="Close player inspector"
        onClick={onClose}
      >
        Close
      </button>
    </div>
  );
}
