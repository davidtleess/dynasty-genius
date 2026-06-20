import { z } from "zod";

// F4: enforce the status enum so the UI parse catches backend contract drift.
export const zPlanStatus = z.enum([
  "planned",
  "in_progress",
  "done",
  "blocked",
  "deferred",
]);
export const zPlanTask = z.object({
  id: z.string(),
  title: z.string(),
  status: zPlanStatus,
  note: z.string().nullable().optional(),
});
export const zPlanPhase = z.object({
  id: z.string(),
  title: z.string(),
  status: zPlanStatus,
  summary: z.string().nullable().optional(),
  tasks: z.array(zPlanTask),
});
export const zProjectPlan = z.object({
  source: z.string(),
  schema_version: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
  phases: z.array(zPlanPhase),
  warnings: z.array(z.string()),
  parser_version: z.string(),
  status: z.enum(["ok", "degraded"]),
});
export type ProjectPlan = z.infer<typeof zProjectPlan>;
