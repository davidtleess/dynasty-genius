// Single source of truth for trust-surface copy that carries constitutional weight.
//
// The non-decision-grade qualifier MUST accompany every rendering of overall_grade so the
// grade can never be read as a market-edge or decision-support claim. Consumed by both the
// Model Trust Console footer (ProvenanceFooter) and the persistent shell TrustStrip — one
// constant, so the two surfaces can never drift apart on the framing.
export const MODEL_GRADE_QUALIFIER =
  "internal model grade — not a market-edge or decision-support claim";
