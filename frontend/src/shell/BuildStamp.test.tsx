// @vitest-environment jsdom

// DG-076: the served page can always say what build it is. The stamp lives in
// the status drawer's receipts panel — one press away, never new chrome — and
// fails silent-honest: no manifest, no stamp; never a fabricated identity.

import { render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ShellStatusDrawer } from "./ShellStatusDrawer";

const SOURCE_SHA = "0123456789abcdef0123456789abcdef01234567";
const OPENAPI_SHA256 =
  "89abcdef89abcdef89abcdef89abcdef89abcdef89abcdef89abcdef89abcdef";
// 2026-08-29T22:15Z is 6:15 PM America/New_York (EDT).
const BUILT_AT = "2026-08-29T22:15:00.000Z";
const MANIFEST_URL = "/assets/build-manifest.json";

function manifest(overrides = {}) {
  return {
    built_at: BUILT_AT,
    openapi_sha256: OPENAPI_SHA256,
    source_sha: SOURCE_SHA,
    ...overrides,
  };
}

function okJson(body: unknown) {
  return { ok: true, status: 200, json: vi.fn().mockResolvedValue(body) };
}

function failedJson(status: number) {
  return { ok: false, status, json: vi.fn().mockResolvedValue({}) };
}

async function renderStamp(response: unknown) {
  globalThis.fetch = vi.fn().mockResolvedValue(response);
  const { BuildStamp } = await import("./BuildStamp");
  return render(<BuildStamp />);
}

async function settled() {
  await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledTimes(1));
  await new Promise((resolve) => setTimeout(resolve, 0));
}

describe("BuildStamp (DG-076 build manifest surface)", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders build sha, schema hash, and ET build time from a valid manifest", async () => {
    await renderStamp(okJson(manifest()));

    const stamp = await screen.findByTestId("dg-build-stamp");
    expect(globalThis.fetch).toHaveBeenCalledWith(MANIFEST_URL);
    expect(stamp.textContent).toContain("Build 0123456");
    expect(stamp.textContent).toContain("schema 89abcdef");
    expect(stamp.textContent).toContain("Aug 29, 6:15 PM ET");
    // Full receipts stay one press away in title text, never truncated away.
    expect(within(stamp).getByTitle(new RegExp(SOURCE_SHA))).toBeTruthy();
    expect(within(stamp).getByTitle(new RegExp(OPENAPI_SHA256))).toBeTruthy();
    const time = stamp.querySelector("time");
    expect(time?.getAttribute("dateTime")).toBe(BUILT_AT);
  });

  it("renders nothing when the manifest is missing (404) — a dev server has no build", async () => {
    await renderStamp(failedJson(404));
    await settled();
    expect(screen.queryByTestId("dg-build-stamp")).toBeNull();
  });

  it("renders nothing when the manifest fetch fails outright", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("network down"));
    const { BuildStamp } = await import("./BuildStamp");
    render(<BuildStamp />);
    await settled();
    expect(screen.queryByTestId("dg-build-stamp")).toBeNull();
    expect(document.body.textContent).not.toContain("network down");
  });

  it("renders nothing on manifest shape drift rather than an unverified identity", async () => {
    await renderStamp(okJson(manifest({ source_sha: "not-a-sha" })));
    await settled();
    expect(screen.queryByTestId("dg-build-stamp")).toBeNull();
  });

  it("keeps the build identity but fabricates no time when built_at is unreadable", async () => {
    await renderStamp(okJson(manifest({ built_at: "not-a-date" })));

    const stamp = await screen.findByTestId("dg-build-stamp");
    expect(stamp.textContent).toContain("Build 0123456");
    expect(stamp.textContent).not.toContain("ET");
    expect(document.body.textContent).not.toMatch(/Invalid Date/i);
    expect(document.body.textContent).not.toMatch(/NaN/);
  });

  it("surfaces the stamp inside the status drawer's receipts panel, not as new chrome", async () => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url === MANIFEST_URL) return Promise.resolve(okJson(manifest()));
      return Promise.resolve(failedJson(503));
    });

    render(<ShellStatusDrawer />);

    const stamp = await screen.findByTestId("dg-build-stamp");
    expect(stamp.closest(".dg-status-drawer__panel")).not.toBeNull();
    expect(stamp.textContent).toContain("Build 0123456");
  });
});
