// @vitest-environment jsdom

import { render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "../shell/AppShell";
import componentSource from "./SystemHealthCard.tsx?raw";

const DISCLAIMER =
  "System health reflects pipeline completion, artifact freshness, and model provenance verification. It does not evaluate model accuracy or guarantee trade edge.";
const FIXED_NOW = new Date("2026-07-03T15:00:00.000Z");
const CHECKED_AT = "2026-07-03T14:55:00+00:00";
const COMPONENT_MODULE = "./SystemHealthCard";

type MockResponse = {
  ok: boolean;
  status: number;
  json: () => Promise<unknown>;
};

function report(overrides = {}) {
  return {
    age_seconds: 300,
    artifact_id: "pvo_refresh",
    artifact_path: "app/data/pvo/pvo_latest.json",
    basis: "embedded_timestamp_fresh",
    decision_supported: false,
    disclosures: [],
    observed_at: "2026-07-03T14:55:00+00:00",
    producer: "scripts/build_universe_pvo_batch.py",
    status: "fresh",
    tier: "core_substrate",
    ...overrides,
  };
}

function subsystem(overrides = {}) {
  return {
    basis: "adapter_status:ok",
    decision_supported: false,
    status: "ok",
    subsystem_id: "model_provenance",
    tier: "core_substrate",
    ...overrides,
  };
}

function healthResponse(overrides = {}) {
  return {
    checked_at: CHECKED_AT,
    config_version: 1,
    decision_supported: false,
    disclaimer: DISCLAIMER,
    overall_status: "ok",
    reports: [
      report(),
      report({
        age_seconds: null,
        artifact_id: "feature_refresh",
        basis: "dormant_ok_offseason",
        observed_at: null,
        status: "dormant",
        tier: "daily_diagnostics",
      }),
      report({
        age_seconds: 3660,
        artifact_id: "what_changed",
        basis: "within_grace",
        observed_at: "2026-07-03T13:59:00+00:00",
        status: "freshness_overdue",
        tier: "daily_diagnostics",
      }),
    ],
    subsystems: [
      subsystem({ subsystem_id: "model_provenance", tier: "core_substrate" }),
      subsystem({ subsystem_id: "capture_health", tier: "core_substrate" }),
      subsystem({ subsystem_id: "tier_readiness", tier: "daily_diagnostics" }),
    ],
    worst_affected_tier: null,
    ...overrides,
  };
}

function okJson(body: unknown): MockResponse {
  return { ok: true, status: 200, json: vi.fn().mockResolvedValue(body) };
}

function failedJson(status: number, body: unknown): MockResponse {
  return { ok: false, status, json: vi.fn().mockResolvedValue(body) };
}

async function renderCard(body: unknown, response: Partial<MockResponse> = {}) {
  globalThis.fetch = vi.fn().mockResolvedValue({ ...okJson(body), ...response });
  const { SystemHealthCard } = await import(/* @vite-ignore */ COMPONENT_MODULE);
  render(<SystemHealthCard now={FIXED_NOW} />);
}

describe("SystemHealthCard RED contract", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders sanitized unavailable state for a parseable 503 body", async () => {
    await renderCard(
      {
        decision_supported: false,
        error: "system_health_unavailable",
        message: "system health configuration unavailable",
      },
      failedJson(503, {
        decision_supported: false,
        error: "system_health_unavailable",
        message: "system health configuration unavailable",
      }),
    );

    await screen.findByText(/data freshness unavailable/i);
    expect(screen.getByText("system health configuration unavailable")).toBeTruthy();
    expect(screen.queryByText(/traceback|stack|exception/i)).toBeNull();
  });

  it("renders the same unavailable state for unparseable 503 bodies and network failure", async () => {
    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 503,
        json: vi.fn().mockRejectedValue(new Error("not json")),
      })
      .mockRejectedValueOnce(new Error("network down"));
    const { SystemHealthCard } = await import(/* @vite-ignore */ COMPONENT_MODULE);

    const { rerender } = render(<SystemHealthCard now={FIXED_NOW} />);
    await screen.findByText(/data freshness unavailable/i);
    expect(screen.queryByText(/not json|network down/i)).toBeNull();

    rerender(<SystemHealthCard now={FIXED_NOW} />);
    await screen.findByText(/data freshness unavailable/i);
    expect(screen.queryByText(/not json|network down/i)).toBeNull();
  });

  it("fails closed on 200 shape drift, wrong types, disclaimer drift, and unknown enums", async () => {
    await renderCard({
      ...healthResponse({
        disclaimer: `${DISCLAIMER} changed`,
        overall_status: "excellent",
      }),
      reports: [report({ age_seconds: "300" })],
    });

    await screen.findByText(/data freshness unavailable/i);
    expect(screen.queryByText("excellent")).toBeNull();
    expect(screen.queryByText("pvo_refresh")).toBeNull();
  });

  it("renders ok with mandatory collapsed counts while keeping dormant and overdue distinct", async () => {
    await renderCard(healthResponse());

    await screen.findByRole("status", { name: "Data freshness" });
    expect(screen.getByText("ok")).toBeTruthy();
    expect(screen.getByText(/3 reports/i)).toBeTruthy();
    expect(screen.getByText(/1 fresh/i)).toBeTruthy();
    expect(screen.getByText(/1 dormant/i)).toBeTruthy();
    expect(screen.getByText(/1 pending/i)).toBeTruthy();
    expect(screen.queryByText(/all systems fresh/i)).toBeNull();

    const dormant = screen.getByTestId("health-report-feature_refresh");
    const overdue = screen.getByTestId("health-report-what_changed");
    expect(dormant.getAttribute("data-health-status")).toBe("dormant");
    expect(dormant.getAttribute("data-severity")).toBeNull();
    expect(overdue.getAttribute("data-health-status")).toBe("freshness_overdue");
    expect(overdue.getAttribute("data-severity")).toBeNull();
    expect(within(overdue).getByText(/within grace/i)).toBeTruthy();
  });

  it("marks only core and daily degraded rows with severity while leaving auxiliary stale informational", async () => {
    await renderCard(
      healthResponse({
        overall_status: "degraded",
        reports: [
          report({
            artifact_id: "core_stale",
            status: "stale",
            tier: "core_substrate",
          }),
          report({
            artifact_id: "daily_missing",
            observed_at: null,
            age_seconds: null,
            status: "missing",
            tier: "daily_diagnostics",
          }),
          report({ artifact_id: "aux_stale", status: "stale", tier: "auxiliary" }),
          report({
            artifact_id: "feature_refresh",
            observed_at: null,
            age_seconds: null,
            status: "dormant",
            tier: "daily_diagnostics",
          }),
        ],
        worst_affected_tier: "core_substrate",
      }),
    );

    await screen.findByText(/degraded/i);
    expect(
      screen.getByTestId("health-report-core_stale").getAttribute("data-severity"),
    ).toBe("degraded");
    expect(
      screen.getByTestId("health-report-daily_missing").getAttribute("data-severity"),
    ).toBe("degraded");
    expect(
      screen.getByTestId("health-report-aux_stale").getAttribute("data-severity"),
    ).toBeNull();
    expect(
      screen.getByTestId("health-report-feature_refresh").getAttribute("data-severity"),
    ).toBeNull();
  });

  it("renders producer_failed as a degrading manager-prose row, not a raw enum", async () => {
    await renderCard(
      healthResponse({
        overall_status: "degraded",
        reports: [
          report({
            artifact_id: "market_divergence",
            artifact_path:
              "app/data/valuation_runtime/market_divergence_refresh_status_latest.json",
            basis: "producer_failure:market_source_prior_date",
            producer: "scripts/run_market_divergence_refresh.py",
            status: "producer_failed",
            tier: "core_substrate",
          }),
        ],
        worst_affected_tier: "core_substrate",
      }),
    );

    const card = await screen.findByRole("status", { name: "Data freshness" });
    expect(within(card).getByText(/1 daily divergence sync failed/i)).toBeTruthy();
    expect(card.textContent).not.toContain("producer_failed");
    const row = await screen.findByTestId("health-report-market_divergence");
    expect(row.getAttribute("data-health-status")).toBe("producer_failed");
    expect(row.getAttribute("data-severity")).toBe("degraded");
    expect(
      within(row).getByText(
        "Daily divergence sync failed. Showing margins from the last successful sync.",
      ),
    ).toBeTruthy();
  });

  it("leads degraded collapsed copy with the worst affected tier and exposes tier severity attributes", async () => {
    await renderCard(
      healthResponse({
        overall_status: "degraded",
        reports: [report({ artifact_id: "core_stale", status: "stale" })],
        worst_affected_tier: "core_substrate",
      }),
    );

    const card = await screen.findByRole("status", { name: "Data freshness" });
    expect(within(card).getByText(/degraded.*core data affected/i)).toBeTruthy();
    expect(card.getAttribute("data-health-status")).toBe("degraded");
    expect(card.getAttribute("data-affected-tier")).toBe("core_substrate");
  });

  it("renders absent, empty, duplicate, and unknown subsystem rows without silent winners", async () => {
    await renderCard(
      healthResponse({
        subsystems: [
          subsystem({ subsystem_id: "capture_health", status: "ok" }),
          subsystem({
            basis: "adapter_status:unavailable",
            status: "unavailable",
            subsystem_id: "capture_health",
          }),
          subsystem({ subsystem_id: "new_guard", status: "degraded" }),
        ],
      }),
    );

    await screen.findAllByText("new_guard");
    expect(
      screen.getByText(/model_provenance.*not reported.*unverified/i),
    ).toBeTruthy();
    expect(screen.getByText(/tier_readiness.*not reported.*unverified/i)).toBeTruthy();
    expect(screen.getAllByText("capture_health")).toHaveLength(2);
    // An unknown subsystem has no display name, so its raw id renders in both the
    // name slot (fallback) and the disclosed receipt — surfaced, never dropped.
    expect(screen.getAllByText("new_guard")).toHaveLength(2);
  });

  it("renders empty report and subsystem collections without fabricating healthy rows", async () => {
    await renderCard(healthResponse({ reports: [], subsystems: [] }));

    await screen.findByText(/no report freshness rows reported/i);
    expect(screen.queryByText(/1 fresh|fresh ·/i)).toBeNull();
    for (const id of ["model_provenance", "capture_health", "tier_readiness"]) {
      expect(
        screen.getByText(new RegExp(`${id}.*not reported.*unverified`, "i")),
      ).toBeTruthy();
    }
  });

  it("renders null, malformed, future, and negative timestamp fields without Invalid Date or negative ages", async () => {
    await renderCard(
      healthResponse({
        checked_at: "not-a-date",
        reports: [
          report({
            age_seconds: null,
            artifact_id: "missing_report",
            observed_at: null,
            status: "missing",
          }),
          report({
            age_seconds: 60,
            artifact_id: "bad_date",
            observed_at: "still-not-a-date",
          }),
          report({
            age_seconds: -3600,
            artifact_id: "future_report",
            observed_at: "2026-07-03T16:00:00+00:00",
          }),
        ],
      }),
    );

    await screen.findByText("not-a-date");
    expect(screen.getAllByText(/timestamp unavailable/i).length).toBeGreaterThanOrEqual(
      1,
    );
    expect(screen.getByText(/no observable timestamp/i)).toBeTruthy();
    expect(screen.getByText("still-not-a-date")).toBeTruthy();
    expect(screen.getByText("2026-07-03T16:00:00+00:00")).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/Invalid Date/i);
    expect(document.body.textContent).not.toMatch(/NaN/);
    expect(document.body.textContent).not.toMatch(/-\d+\s*(s|m|h|sec|min|hour)/i);
  });

  it("renders the exact disclaimer and descriptive disclosure in accessible text", async () => {
    await renderCard(healthResponse());

    await screen.findByText(DISCLAIMER);
    expect(screen.getByText("Descriptive only — not decision-grade.")).toBeTruthy();
    expect(screen.queryByText(/decision_supported=false/i)).toBeNull();
  });

  it("keeps long report metadata contained by CSS rather than truncating disclosed text", async () => {
    await renderCard(
      healthResponse({
        reports: [
          report({
            artifact_id:
              "very_long_artifact_id_that_should_wrap_without_breaking_the_shell",
            artifact_path:
              "app/data/reports/very/deep/path/that/should/remain/disclosed/latest.json",
            basis: "very_long_basis_token_that_should_remain_visible",
            producer: "scripts/very_long_producer_name_that_should_remain_visible.py",
          }),
        ],
      }),
    );

    const row = await screen.findByTestId(
      "health-report-very_long_artifact_id_that_should_wrap_without_breaking_the_shell",
    );
    expect(row.textContent).toContain(
      "very_long_artifact_id_that_should_wrap_without_breaking_the_shell",
    );
    expect(row.textContent).toContain(
      "app/data/reports/very/deep/path/that/should/remain/disclosed/latest.json",
    );
    expect(row.textContent).toContain(
      "very_long_basis_token_that_should_remain_visible",
    );
    expect(row.textContent).toContain(
      "scripts/very_long_producer_name_that_should_remain_visible.py",
    );
    expect(row.className).toContain("dg-syshealth__report");
  });

  it("renders deterministic relative checked_at age with the absolute timestamp in title text", async () => {
    await renderCard(healthResponse());

    const checkedAt = await screen.findByTitle(CHECKED_AT);
    expect(checkedAt.textContent).toMatch(/5\s*(minutes|min|m)/i);
    expect(checkedAt.getAttribute("title")).toBe(CHECKED_AT);
  });

  it("mounts in the AppShell header alongside the existing TrustStrip", async () => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url === "/api/health") return Promise.resolve(okJson(healthResponse()));
      if (url === "/api/trust-surface/QB") {
        return Promise.resolve(failedJson(503, { detail: "trust unavailable" }));
      }
      return Promise.resolve(failedJson(404, { detail: "not found" }));
    });

    render(<AppShell />);

    const banner = screen.getByRole("banner", { name: "Trust strip" });
    expect(
      within(banner).getByRole("status", { name: "Trust strip status" }),
    ).toBeTruthy();
    await waitFor(() =>
      expect(
        within(banner).getByRole("status", { name: "Data freshness" }),
      ).toBeTruthy(),
    );
  });

  it("keeps authored labels free of affirmative trust, accuracy, verdict, green, and success language", async () => {
    await renderCard(healthResponse());

    const card = await screen.findByRole("status", { name: "Data freshness" });
    const visibleText = card.textContent ?? "";
    const authored = componentSource;
    const allowed = authored
      .replaceAll(DISCLAIMER, "")
      .replaceAll("not model accuracy", "")
      .replaceAll("does not evaluate model accuracy", "");

    expect(visibleText).not.toMatch(/\b(buy|sell|hold|keep|cut|start|sit)\b/i);
    expect(allowed).not.toMatch(
      /\b(System Trust|Model Status|Model Validity|Accuracy|Verified|Trust Score)\b/i,
    );
    expect(allowed).not.toMatch(/\b(green|red|success|pass)\b/i);
    expect(allowed).not.toContain("--dg-market");
  });
});
