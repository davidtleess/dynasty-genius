// DG primitive: player identity — the human face of every row (benchmark
// §2.1). Headshot rendering is gated by the David asset-pipeline decision;
// until then (and whenever an image is missing) the fallback is a named,
// accessible placeholder — never a broken hotlink.
import "./ui.css";

export function PlayerIdentity({
  name,
  team,
  position,
  imageStatus,
}: {
  name: string;
  team: string;
  position: string;
  imageStatus: "available" | "missing";
}) {
  return (
    <span className="dg-ui-player-id">
      {imageStatus === "missing" ? (
        <span
          className="dg-ui-player-id__headshot dg-ui-player-id__headshot--fallback"
          role="img"
          aria-label={`${name} headshot unavailable`}
        >
          {name
            .split(" ")
            .map((part) => part[0])
            .slice(0, 2)
            .join("")}
        </span>
      ) : null}
      <span className="dg-ui-player-id__name">{name}</span>
      <span className="dg-ui-player-id__team" data-team-color-basis={team}>
        {team}
      </span>
      <span className="dg-ui-player-id__position">{position}</span>
    </span>
  );
}
