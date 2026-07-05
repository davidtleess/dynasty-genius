// H2 I1 — the shared endpoint-resource hook (vision spec §4, Codex position 5).
// Small by design, not a data platform: one GET, generated-Zod validation at
// the boundary, a discriminated state, stale-request abort. No caching or
// retry policy until a surface proves the need. Trade Lab POSTs and typeahead
// search stay on their own paths.
import { useEffect, useState } from "react";
import type { ZodType } from "zod";

export type EndpointResourceState<T> =
  | { status: "loading" }
  | { status: "ready"; data: T }
  | { status: "unavailable"; httpStatus: number | null }
  | { status: "parse-error" };

export function useEndpointResource<T>({
  url,
  schema,
}: {
  url: string;
  schema: ZodType<T>;
}): EndpointResourceState<T> {
  const [state, setState] = useState<EndpointResourceState<T>>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });

    async function load() {
      try {
        const response = await fetch(url, { signal: controller.signal });
        if (controller.signal.aborted) {
          return;
        }
        if (!response.ok) {
          setState({ status: "unavailable", httpStatus: response.status });
          return;
        }
        const body: unknown = await response.json();
        if (controller.signal.aborted) {
          return;
        }
        const parsed = schema.safeParse(body);
        if (!parsed.success) {
          setState({ status: "parse-error" });
          return;
        }
        setState({ status: "ready", data: parsed.data });
      } catch {
        // Abort of a stale request is not an error state; anything else on a
        // live request degrades to unavailable (fail-closed, never blank).
        if (!controller.signal.aborted) {
          setState({ status: "unavailable", httpStatus: null });
        }
      }
    }

    void load();
    return () => controller.abort();
    // The schema for a given endpoint is a module-level generated constant;
    // it participates in deps so a different schema is a different resource.
  }, [url, schema]);

  return state;
}
