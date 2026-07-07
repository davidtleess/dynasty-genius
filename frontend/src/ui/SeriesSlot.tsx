// DG primitive: the series slot — honest in every state. Pending renders NO
// path (no fake trends, reset inviolate 2); ready renders history that stops
// dead at the Hard Right Edge (vision §2), with capture gaps drawn AS gaps.
import "./ui.css";

type SeriesPoint = { capturedAt: string; value: number | null };

const WIDTH = 120;
const HEIGHT = 28;
const PAD = 3;

function scale(points: SeriesPoint[]): { x: number; y: number | null }[] {
  const values = points
    .map((p) => p.value)
    .filter((v): v is number => v !== null && Number.isFinite(v));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const step = points.length > 1 ? (WIDTH - PAD * 2) / (points.length - 1) : 0;
  return points.map((p, i) => ({
    x: PAD + i * step,
    y:
      p.value === null || !Number.isFinite(p.value)
        ? null
        : HEIGHT - PAD - ((p.value - min) / span) * (HEIGHT - PAD * 2),
  }));
}

// Consecutive non-null runs become separate polyline segments; null points
// remain visible as gap markers instead of interpolated fiction.
function segments(coords: { x: number; y: number | null }[]): string[] {
  const runs: string[][] = [];
  let current: string[] = [];
  for (const c of coords) {
    if (c.y === null) {
      if (current.length > 0) {
        runs.push(current);
        current = [];
      }
    } else {
      current.push(`${c.x},${c.y}`);
    }
  }
  if (current.length > 0) runs.push(current);
  return runs.filter((r) => r.length > 1).map((r) => r.join(" "));
}

export function SeriesSlot({
  status,
  label,
  summary,
  points,
}: {
  status: "pending" | "ready";
  label: string;
  summary?: string | undefined;
  points?: SeriesPoint[] | undefined;
}) {
  if (status !== "ready" || !points || points.length === 0) {
    return (
      <span className="dg-ui-series dg-ui-series--pending">
        {summary ?? "Series pending"}
      </span>
    );
  }

  const coords = scale(points);
  const lastDrawn = [...coords].reverse().find((c) => c.y !== null);

  return (
    <svg
      className="dg-ui-series"
      role="img"
      aria-label={`${label} — history ends at the hard right edge (last verified capture)`}
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      width={WIDTH}
      height={HEIGHT}
    >
      {segments(coords).map((pts) => (
        <polyline key={pts} className="dg-ui-series__line" points={pts} fill="none" />
      ))}
      {coords.map(
        (c, i) =>
          c.y === null && (
            <line
              // biome-ignore lint/suspicious/noArrayIndexKey: gap position IS the identity
              key={`gap-${i}`}
              data-series-gap="true"
              className="dg-ui-series__gap"
              x1={c.x}
              x2={c.x}
              y1={PAD}
              y2={HEIGHT - PAD}
            />
          ),
      )}
      {lastDrawn && lastDrawn.y !== null && (
        <circle
          // Endpoint dot (fresh-agent reviews): the last verified capture is a
          // POINT the eye can land on; the edge tick alone read as an artifact.
          data-series-endpoint="true"
          className="dg-ui-series__endpoint"
          cx={lastDrawn.x}
          cy={lastDrawn.y}
          r={2.5}
        />
      )}
      {lastDrawn && lastDrawn.y !== null && (
        <line
          data-hard-right-edge="true"
          className="dg-ui-series__edge"
          x1={lastDrawn.x}
          x2={lastDrawn.x}
          y1={Math.max(PAD, lastDrawn.y - 6)}
          y2={Math.min(HEIGHT - PAD, lastDrawn.y + 6)}
        />
      )}
    </svg>
  );
}
