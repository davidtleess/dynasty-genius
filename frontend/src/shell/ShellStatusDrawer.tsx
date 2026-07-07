// H2 worklist #1 (fresh-agent reviews, both): the shell chrome — model-grade
// provenance strip + System Diagnostics card — collapses behind ONE compact
// status pill. The first viewport belongs to the product, not the plumbing;
// the plumbing stays one press away (visible ≠ wallpaper). The drawer expands
// IN FLOW (accordion) so nothing ever overlaps content at any scroll position
// — the overlay-collision class of bug is structurally impossible here.
import { useEffect, useState } from "react";
import { zSystemHealthResponse } from "../lib/api/zod.gen";
import { SystemHealthCard } from "../system-health/SystemHealthCard";
import "./ShellStatusDrawer.css";
import { TrustStrip } from "./TrustStrip";

type PillState =
  | { status: "loading" }
  | { status: "ok"; checkedAt?: string }
  | { status: "degraded" }
  | { status: "unavailable" };

const PILL_TIME = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/New_York",
  hour: "numeric",
  minute: "2-digit",
});

export function ShellStatusDrawer() {
  const [open, setOpen] = useState(false);
  const [pill, setPill] = useState<PillState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/health");
        if (!res.ok) {
          if (!cancelled) setPill({ status: "unavailable" });
          return;
        }
        const parsed = zSystemHealthResponse.safeParse(await res.json());
        if (!parsed.success) {
          if (!cancelled) setPill({ status: "unavailable" });
          return;
        }
        if (!cancelled) {
          if (parsed.data.overall_status !== "ok") {
            setPill({ status: "degraded" });
          } else {
            // Freshness must come from the payload's own checked_at, not the
            // client clock (Codex trust-surface finding): the pill states when
            // the health check actually ran, server-side. An unreadable stamp
            // shows "Synced" with no fabricated time rather than overstating it.
            const checked = new Date(parsed.data.checked_at);
            setPill({
              status: "ok",
              ...(Number.isNaN(checked.getTime())
                ? {}
                : { checkedAt: PILL_TIME.format(checked) }),
            });
          }
        }
      } catch {
        if (!cancelled) setPill({ status: "unavailable" });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const pillText =
    pill.status === "ok"
      ? pill.checkedAt
        ? `Synced · ${pill.checkedAt} ET`
        : "Synced"
      : pill.status === "degraded"
        ? "Attention — details inside"
        : pill.status === "unavailable"
          ? "Status unavailable"
          : "Checking…";

  return (
    <div className="dg-status-drawer">
      <button
        type="button"
        className="dg-status-drawer__pill"
        aria-expanded={open}
        data-pill-status={pill.status}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="dg-status-drawer__dot" aria-hidden="true" />
        {pillText}
      </button>
      <div className="dg-status-drawer__panel" data-open={open ? "true" : "false"}>
        {/* Both trust surfaces stay mounted (contracts + live data); the
            drawer only governs visibility. Distinct axes, never merged. */}
        <TrustStrip position="QB" />
        <SystemHealthCard />
      </div>
    </div>
  );
}
