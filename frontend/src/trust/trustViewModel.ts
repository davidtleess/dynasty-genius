// Model Trust Console — curated view-model (T5). THE ANTI-LEAKAGE BOUNDARY.
//
// The broad BacktestResult-superset trust-surface shape (ridge_alpha, retrain_mode,
// rmse_stability, schema_version, ...) and the model-card provenance fields stop here.
// The panels (T6-T9) consume only `TrustConsoleViewModel`, never the raw responses.
import type { z } from "zod";

import type { zModelCardResponse, zTrustSurfaceResponse } from "../lib/api/zod.gen";

export type TrustSurfaceData = z.infer<typeof zTrustSurfaceResponse>;
export type ModelCardData = z.infer<typeof zModelCardResponse>;

export type TrustConsoleViewModel = {
  position: string;
  overall_grade: string;
  experimental: boolean;
  gates: TrustSurfaceData["promotion_gate"];
  folds: TrustSurfaceData["folds"];
  model_reliability: TrustSurfaceData["model_reliability"];
  market: {
    source: string;
    label: string;
    snapshot_dates: TrustSurfaceData["market_snapshot_dates"];
  };
  provenance: {
    run_id: string | null;
    run_date: string;
    model_version: string;
    model_artifact_hash: string;
    git_sha: string | null;
  };
  model_card: ModelCardData | null;
};

export function buildTrustConsoleViewModel(
  trustSurface: TrustSurfaceData,
  modelCard: ModelCardData | null,
): TrustConsoleViewModel {
  return {
    position: trustSurface.position,
    overall_grade: trustSurface.overall_grade,
    experimental: trustSurface.experimental,
    gates: trustSurface.promotion_gate,
    folds: trustSurface.folds,
    model_reliability: trustSurface.model_reliability ?? null,
    market: {
      source: trustSurface.market_source,
      label: trustSurface.market_source_label,
      snapshot_dates: trustSurface.market_snapshot_dates ?? null,
    },
    provenance: {
      run_id: trustSurface.run_id ?? null,
      run_date: trustSurface.run_date,
      model_version: trustSurface.model_version,
      model_artifact_hash: trustSurface.model_artifact_hash,
      git_sha: trustSurface.git_sha ?? null,
    },
    // The public ModelCardResponse already carries the 8 curated fields only — no
    // model_version/model_artifact_hash/git_sha — so this never leaks provenance.
    model_card: modelCard,
  };
}
