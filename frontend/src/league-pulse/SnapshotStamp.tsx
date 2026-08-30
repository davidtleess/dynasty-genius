// The league snapshot's freshness stamp — the two facts the producer emits on
// EVERY /api/league/pulse response, extracted so they can render wherever a
// panel built from that snapshot renders.
//
// DG-114 REVIEW FIX. Partner Rankings moved from League Pulse to Trades and
// only the posture disclosure travelled with it. These two did not, and they
// are producer-emitted, not decorative: league_pulse_assembler.py returns
// `status="degraded"` with `captured_at` and
// `caveats=["league_pulse_artifact_state_<date>"]` on every single response
// (:306-348). On League those reached the screen through LeaguePulseHeader; at
// the panel's new address nothing said how old the data was, so a stale
// snapshot would have printed eleven priced partner cards with no date on
// screen. The honesty law is "stale must still say it is stale" — that is a
// property of the DATA, so it belongs with the panel, not with an address.
import { describeToken, formatCaptureTimestamp } from "../lib/copy";

export function SnapshotStamp({
  capturedAt,
  caveats,
}: {
  capturedAt: string | null | undefined;
  caveats: string[] | null | undefined;
}) {
  const artifactStateCaveat = (caveats ?? []).find((c) =>
    c.startsWith("league_pulse_artifact_state_"),
  );

  return (
    <>
      <p className="dg-league-pulse__asof" title={capturedAt ?? undefined}>
        as of {formatCaptureTimestamp(capturedAt)}
      </p>
      {artifactStateCaveat ? (
        // DG-109 translates the token; DG-111 keeps the verbatim token on the
        // element, so the humanized sentence is a translation and never a
        // deletion.
        <p className="dg-league-pulse__caveat" title={artifactStateCaveat}>
          {describeToken(artifactStateCaveat)}
        </p>
      ) : null}
    </>
  );
}
