// DG-203 — where the player sits in the one common population, on both readings.
//
// The imported version drew a value curve from the alternate model. This draws only what the accepted
// source carries: two rank intervals on one shared axis, best on the left. A tie is drawn as the span
// it really is; its minimum visible width lives in the style, never in the number, so a single rank
// can never be mistaken for a wide tie.
import { rankLabel, type RankInterval } from "@/lib/dg/backend";

function place(rank: number, total: number) {
  return total <= 1 ? 50 : ((rank - 1) / (total - 1)) * 100;
}

function Lane({ rank, color, label }: { rank: RankInterval | null; color: string; label: string }) {
  if (!rank) {
    return (
      <div className="flex items-baseline gap-2">
        <span className="label-caps" style={{ color }}>
          {label}
        </span>
        <span className="label-caps">Not ranked</span>
      </div>
    );
  }
  const left = place(rank.start, rank.total);
  const width = place(rank.end, rank.total) - left;
  return (
    <div>
      <div className="flex items-baseline gap-2">
        <span className="label-caps" style={{ color }}>
          {label}
        </span>
        <span className="num text-[12px]">{rankLabel(rank)}</span>
      </div>
      <div className="relative mt-1 h-2 rounded-full" style={{ background: "var(--hairline)" }}>
        <div
          className="absolute top-0 h-2 rounded-full"
          style={{
            left: `${left.toFixed(3)}%`,
            width: `${width.toFixed(3)}%`,
            minWidth: 3,
            background: color,
          }}
        />
      </div>
    </div>
  );
}

export function CohortChart({
  ours,
  market,
}: {
  ours: RankInterval | null;
  market: RankInterval | null;
}) {
  const total = ours?.total ?? market?.total ?? null;
  if (total == null) {
    return <p className="label-caps mt-4">No comparable ranking for this player.</p>;
  }
  return (
    <section className="mt-5">
      <h3 className="text-[13px] font-semibold tracking-tight">On one shared scale</h3>
      <p className="label-caps mt-1">{total} players carry both numbers · lower is better</p>
      <div className="mt-3 space-y-3">
        <Lane rank={ours} color="var(--ours)" label="Ours" />
        <Lane rank={market} color="var(--market)" label="Market" />
      </div>
    </section>
  );
}
