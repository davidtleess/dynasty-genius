import { z } from "zod";

export const TradeEvaluationSchema = z.object({
  verdict: z.string().nullable().optional(),
  dynasty_tier: z.string().nullable().optional(),
  confidence: z.string().nullable().optional(),
});
