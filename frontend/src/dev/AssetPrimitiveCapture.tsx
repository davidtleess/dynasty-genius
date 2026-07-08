// H2 Increment 0 — the primitive capture page (evidence surface, URL-only:
// reachable at ?surface=asset-primitive-capture, deliberately absent from the
// rail and command palette; it is a developer evidence target, not a David
// surface). Self-contained: the demo headshot is an inline data URI so the
// page renders identically with no asset cache and no network (CI-safe).
import { MetricCell } from "../ui/MetricCell";
import { PlayerIdentity } from "../ui/PlayerIdentity";
import { SpreadBar } from "../ui/SpreadBar";
import "./AssetPrimitiveCapture.css";

// Inline SVG demo avatar — stands in for a cached headshot without touching
// app/data or the network; visibly a portrait so the "image available" state
// reads differently from the initials fallback in captures.
const DEMO_HEADSHOT = `data:image/svg+xml,${encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" fill="#3a4254"/><circle cx="24" cy="18" r="8" fill="#9aa4bd"/><path d="M8 44c2-10 9-14 16-14s14 4 16 14z" fill="#9aa4bd"/></svg>',
)}`;

export function AssetPrimitiveCapture() {
  return (
    <section className="dg-asset-capture" aria-label="Primitive capture states">
      <p className="dg-asset-capture__intro">
        Increment-0 primitive states for the evidence bundle: identity fallback chain,
        lane-isolated spreads, and the row-focal value. Capture only — not a pass gate
        on its own; the recorded axe result is the gate.
      </p>

      <h2 className="dg-asset-capture__heading">Identity fallback chain</h2>
      <ul className="dg-asset-capture__list">
        <li>
          <PlayerIdentity
            name="Bijan Robinson"
            team="ATL"
            position="RB"
            imageStatus="available"
            imageSrc={DEMO_HEADSHOT}
            teamId="ATL"
            positionRank="RB1"
          />
        </li>
        <li>
          <PlayerIdentity
            name="Jaxon Smith-Njigba"
            team="SEA"
            position="WR"
            imageStatus="missing"
            teamId="SEA"
            positionRank="WR4"
          />
        </li>
        <li>
          <PlayerIdentity name="Neymar" team="" position="WR" imageStatus="missing" />
        </li>
      </ul>

      <h2 className="dg-asset-capture__heading">Lane-isolated spreads</h2>
      <ul className="dg-asset-capture__list">
        <li>
          <SpreadBar
            label="Model range"
            value={12.5}
            sigma={2.1}
            basis="model percentile spread"
            pct={62}
            lane="model"
          />
        </li>
        <li>
          <SpreadBar
            label="Market range"
            value={8.4}
            basis="market percentile spread"
            pct={44}
            lane="market"
          />
        </li>
      </ul>

      <h2 className="dg-asset-capture__heading">Row-focal value</h2>
      <ul className="dg-asset-capture__list">
        <li>
          <MetricCell label="model value percentile" value="94%" emphasis="row-focal" />
        </li>
        <li>
          <MetricCell label="age" value="24.4" />
        </li>
      </ul>
    </section>
  );
}
