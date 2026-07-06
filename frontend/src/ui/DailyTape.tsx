// DG primitive: the daily tape — substrate facts in dynasty-manager PROSE
// (voice guide §3); raw technical values live one layer down in title attrs.
// Never movement or trend claims.
import "./ui.css";

const TAPE_DATE = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/New_York",
  month: "long",
  day: "numeric",
});

function tapeDate(iso: string): string {
  const parsed = Date.parse(iso);
  return Number.isNaN(parsed) ? iso : TAPE_DATE.format(new Date(parsed));
}

export function DailyTape({
  capture,
  provenance,
}: {
  capture: { consecutiveDays: number; lastCaptureAt: string; status: string };
  provenance: { registryVersion: number; modelVintage: string; status: string };
}) {
  const healthy = capture.status === "ok" && provenance.status === "ok";

  return (
    <section className="dg-ui-tape" aria-label="Daily tape">
      <span
        className="dg-ui-tape__fact"
        title={`consecutive_days=${capture.consecutiveDays} last_capture_at=${capture.lastCaptureAt}`}
      >
        {capture.status === "ok"
          ? `Market Sync Active: ${capture.consecutiveDays} consecutive days tracked`
          : "Partial Market Sync: some inputs are being verified"}
      </span>
      <span
        className="dg-ui-tape__fact"
        title={`registry_version=${provenance.registryVersion} model_vintage=${provenance.modelVintage}`}
      >
        {provenance.status === "ok"
          ? `Projection Update: ${tapeDate(capture.lastCaptureAt)}, current`
          : "Projections active using the latest verified data"}
      </span>
      <span className="dg-ui-tape__fact">
        {healthy ? "Status: Synced" : "Status: Degraded"}
      </span>
    </section>
  );
}
