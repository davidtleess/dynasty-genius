export function FieldLabelProse({ card }: { card: { pct: number; tier: string } }) {
  return (
    <section>
      <h2>Week 3 outlook</h2>
      <p>Sell high on him while the market is hot.</p>
      <p>He is a must start against a soft secondary.</p>
      <p>Strong win expectancy through the playoff weeks.</p>
      <p>Buy low on the rookie behind him.</p>
      <p>Confidence score: {card.pct}%</p>
      <p>Dynasty tier: {card.tier}</p>
    </section>
  );
}
