// DG primitive: every chart lives in a frame that carries its title, the
// standard disclosure, and an honest summary of where the data ENDS. No
// extrapolation copy can enter through this frame.
import { DisclosureLine } from "./DisclosureLine";
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
      <DisclosureLine />
    </figure>
  );
}
