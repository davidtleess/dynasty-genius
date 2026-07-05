// @vitest-environment jsdom

import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { z } from "zod";

import { useEndpointResource } from "./useEndpointResource";

const payloadSchema = z.object({
  id: z.string(),
  count: z.number(),
});

type Payload = z.infer<typeof payloadSchema>;

function deferredResponse(body: unknown, init: { ok?: boolean; status?: number } = {}) {
  let resolveResponse: (value: Response) => void = () => undefined;
  const promise = new Promise<Response>((resolve) => {
    resolveResponse = resolve;
  });
  return {
    promise,
    resolve: () =>
      resolveResponse({
        ok: init.ok ?? true,
        status: init.status ?? 200,
        json: async () => body,
      } as Response),
  };
}

describe("useEndpointResource", () => {
  it("returns loading then ready with generated-Zod validated data", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: "alpha", count: 7 }),
    });

    const { result } = renderHook(() =>
      useEndpointResource<Payload>({ url: "/api/example", schema: payloadSchema }),
    );

    expect(result.current.status).toBe("loading");
    await waitFor(() => expect(result.current.status).toBe("ready"));
    expect(result.current).toMatchObject({
      status: "ready",
      data: { id: "alpha", count: 7 },
    });
  });

  it("maps non-OK responses to unavailable and schema violations to parse-error", async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({ detail: "offline" }),
    });

    const unavailable = renderHook(() =>
      useEndpointResource<Payload>({ url: "/api/example", schema: payloadSchema }),
    );
    await waitFor(() => expect(unavailable.result.current.status).toBe("unavailable"));

    globalThis.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ id: "alpha", count: "not-a-number" }),
    });
    const parseError = renderHook(() =>
      useEndpointResource<Payload>({ url: "/api/example", schema: payloadSchema }),
    );
    await waitFor(() => expect(parseError.result.current.status).toBe("parse-error"));
  });

  it("aborts stale requests and prevents stale responses from overwriting newer data", async () => {
    const first = deferredResponse({ id: "first", count: 1 });
    const second = deferredResponse({ id: "second", count: 2 });
    const signals: AbortSignal[] = [];
    globalThis.fetch = vi
      .fn()
      .mockImplementationOnce((_url, init?: RequestInit) => {
        signals.push(init?.signal as AbortSignal);
        return first.promise;
      })
      .mockImplementationOnce((_url, init?: RequestInit) => {
        signals.push(init?.signal as AbortSignal);
        return second.promise;
      });

    const { result, rerender } = renderHook(
      ({ url }) => useEndpointResource<Payload>({ url, schema: payloadSchema }),
      { initialProps: { url: "/api/one" } },
    );

    rerender({ url: "/api/two" });
    expect(signals[0]).toBeDefined();
    expect(signals[0]?.aborted).toBe(true);

    await act(async () => second.resolve());
    await waitFor(() =>
      expect(result.current).toMatchObject({
        status: "ready",
        data: { id: "second", count: 2 },
      }),
    );

    await act(async () => first.resolve());
    expect(result.current).toMatchObject({
      status: "ready",
      data: { id: "second", count: 2 },
    });
  });
});
