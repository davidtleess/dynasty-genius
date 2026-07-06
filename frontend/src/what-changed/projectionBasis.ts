// Voice-guide translation layer (H2 reset Task 5): the surface speaks manager
// prose; raw model-output fingerprints stay one layer down in the title/receipt
// layer. This module owns the raw vintage field names so the surface file
// never carries backend nouns in its copy or its code.
import type { WhatChangedModelSection } from "../lib/api/types.gen";

type ModelComparisonWindow = WhatChangedModelSection["comparison_window"];

// Raw receipt string for the projection-basis line's title layer, or null when
// either side of the window has no verified fingerprint (no fabricated basis).
export function projectionBasisTitle(window: ModelComparisonWindow): string | null {
  const fromHash = window?.from_vintage?.semantic_output_hash ?? null;
  const toHash = window?.to_vintage?.semantic_output_hash ?? null;
  if (!fromHash || !toHash) {
    return null;
  }
  return `model output fingerprint ${fromHash} → ${toHash}`;
}
