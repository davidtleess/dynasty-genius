// DG primitive: every chart lives in a frame that carries its title and an
// honest summary of where the data ENDS. No extrapolation copy can enter
// through this frame.
//
// DG-111: the frame no longer stamps "Descriptive only — not decision-grade."
// under every chart. The summary — which says in words where the data stops —
// was always the honest half; the stamp was furniture repeated per chart.
import "./ui.css";

export function ChartFrame({
  title,
  summary,
  children,
}: {
  title: string;
  summary: string;
  children: React.ReactNode;
}) {
  return (
    <figure className="dg-ui-chart-frame" aria-label={title}>
      <figcaption className="dg-ui-chart-frame__title">{title}</figcaption>
      <div className="dg-ui-chart-frame__body">{children}</div>
      <p className="dg-ui-chart-frame__summary">{summary}</p>
    </figure>
  );
}
