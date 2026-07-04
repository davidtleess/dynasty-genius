// A lane that could not be loaded — missing model artifacts (503, which
// coupledly fails both lanes) or a 200 that failed schema validation. It never
// implies the surviving lane is decision-grade.
export function LaneDegradedState({ label }: { label: string }) {
  return (
    <section
      className="dg-lane dg-lane--degraded"
      data-visual-weight="equal"
      data-lane="degraded"
      role="status"
      aria-label={`${label} unavailable`}
    >
      <p className="dg-lane__title">{label} unavailable</p>
      <p>This lane could not be loaded.</p>
    </section>
  );
}
