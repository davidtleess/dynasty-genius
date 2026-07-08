// DG primitive: the standard region caveat — high-contrast neutral (or
// structural-amber) disclosure block, single instance per region, never a
// card nested inside a card (reset spec Task 2).
import "./ui.css";

export function CaveatBlock({
  tone,
  title,
  items,
}: {
  tone: "neutral" | "structural";
  title: string;
  items: string[];
}) {
  return (
    <aside className="dg-ui-caveat" role="note" aria-label={title} data-tone={tone}>
      <span className="dg-ui-caveat__title">{title}</span>
      <ul className="dg-ui-caveat__items">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </aside>
  );
}
