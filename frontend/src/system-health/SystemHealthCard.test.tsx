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

// The whole text of the subsystem row that leads with `name` — the name and the
// state live in sibling spans, so the assertion has to read the row, not a node.
function subsystemRowText(name: string): string {
  const row = screen.getByText(name).closest("li");
  expect(row).toBeTruthy();
  return row?.textContent ?? "";
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
    // DG-109 review fix: the headline may claim ONLY what the rollup checked.
    // `rollup_health_status` scores core-substrate and daily-diagnostics rows
    // and nothing else (_TIER_SEVERITY has no `auxiliary` key), and neither
    // `freshness_overdue` nor `dormant` degrades anything — so an earlier draft
    // reading "Nothing needs attention" was wider than the rollup and could be
    // contradicted by the card's own rows. This fixture is the quiet case: one
    // fresh, one dormant, one overdue, nothing degrading anywhere.
    expect(screen.getByText("No main feed is stale, missing or failed")).toBeTruthy();
    expect(screen.queryByText(/nothing needs attention/i)).toBeNull();
    expect(screen.queryByText("ok")).toBeNull();
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

    // DG-109: `degraded` is not a claim about LATENESS — the rollup raises it for
    // a stale, unreadable, missing or failed feed alike, and "Running behind"
    // understated every one of those but the first.
    await screen.findByText(/something needs attention/i);
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

  // The amber-blindness case, and the reason the ok line was rewritten. The
  // backend's rollup DELIBERATELY ignores auxiliary rows (system_health_models.py
  // :363 `_TIER_SEVERITY` has no `auxiliary` key, and it tags the suppression
  // `auxiliary_info_only` at :653-654), so `overall_status` is "ok" with a failed
  // auxiliary producer on the same screen. The headline must not swallow that.
  it("does not read as all-clear when a feed outside the rollup's scope has failed", async () => {
    await renderCard(
      healthResponse({
        overall_status: "ok",
        worst_affected_tier: null,
        reports: [
          report(),
          report({
            artifact_id: "league_opportunity",
            status: "producer_failed",
            tier: "auxiliary",
            disclosures: ["auxiliary_info_only"],
          }),
        ],
      }),
    );

    const card = await screen.findByRole("status", { name: "Data freshness" });
    expect(
      within(card).getByText(
        "Main feeds are healthy — one feed outside them is not; it is listed below",
      ),
    ).toBeTruthy();
    expect(within(card).queryByText(/nothing needs attention/i)).toBeNull();
    expect(within(card).queryByText(/no main feed is stale/i)).toBeNull();
    // The row itself still says what happened, in full.
    expect(
      within(card).getByText("Last run failed. Earlier values may still be in use."),
    ).toBeTruthy();
    expect(within(card).getByText(/1 failed/i)).toBeTruthy();
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
    expect(within(card).getByText(/1 failed/i)).toBeTruthy();
    expect(card.textContent).not.toContain("producer_failed");
    const row = await screen.findByTestId("health-report-market_divergence");
    expect(row.getAttribute("data-health-status")).toBe("producer_failed");
    expect(row.getAttribute("data-severity")).toBe("degraded");
    expect(
      within(row).getByText("Last run failed. Earlier values may still be in use."),
    ).toBeTruthy();
  });

  it("names the failing artifact without blaming a different subsystem (DG-033)", async () => {
    // The producer_failed copy hardcoded "daily divergence sync failed" for EVERY
    // artifact. pvo_refresh renders as "Model valuations", so an aborted valuation
    // run told the manager the divergence sync broke and that they were looking at
    // last-good margins — wrong subsystem, wrong claim. DG-033 declares
    // pvo_refresh's status_field, which is what makes this row reachable at all.
    await renderCard(
      healthResponse({
        overall_status: "degraded",
        reports: [
          report({
            artifact_id: "pvo_refresh",
            artifact_path: "app/data/model_capture/pvo_refresh_latest_report.json",
            basis: "producer_failure:refresh stage raised",
            producer: "scripts/run_pvo_refresh.py",
            status: "producer_failed",
            tier: "core_substrate",
          }),
        ],
        worst_affected_tier: "core_substrate",
      }),
    );

    const row = await screen.findByTestId("health-report-pvo_refresh");
    expect(within(row).getByText("Model valuations")).toBeTruthy();
    expect(row.textContent).not.toMatch(/divergence/i);
    expect(row.textContent).not.toMatch(/margins/i);

    const card = await screen.findByRole("status", { name: "Data freshness" });
    expect(card.textContent).not.toMatch(/divergence/i);
    expect(card.textContent).not.toContain("producer_failed");
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
    // Both facts stay: that it is degraded, and WHICH tier is affected.
    expect(
      within(card).getByText(/something needs attention.*core data affected/i),
    ).toBeTruthy();
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

    await screen.findAllByText(/new guard/i);
    // An absent guard is still explicitly unverified — DG-109 only changes the
    // words. The guard is named, and the sentence still says we could not
    // verify it.
    expect(subsystemRowText("Model provenance")).toMatch(
      /not reported.*could not verify/i,
    );
    expect(subsystemRowText("Tier readiness")).toMatch(
      /not reported.*could not verify/i,
    );
    // The duplicate id still surfaces as a visible conflict: one name row plus
    // one receipt row per payload entry.
    expect(screen.getAllByText("Capture health")).toHaveLength(2);
    expect(screen.getAllByText("capture_health")).toHaveLength(2);
    // An unknown subsystem has no dictionary entry, so its id humanizes in the
    // name slot and stays verbatim in the disclosed receipt — never dropped.
    expect(screen.getAllByText("New guard")).toHaveLength(1);
    expect(screen.getAllByText("new_guard")).toHaveLength(1);
  });

  it("renders empty report and subsystem collections without fabricating healthy rows", async () => {
    await renderCard(healthResponse({ reports: [], subsystems: [] }));

    await screen.findByText(/no report freshness rows reported/i);
    expect(screen.queryByText(/1 fresh|fresh ·/i)).toBeNull();
    for (const name of ["Model provenance", "Capture health", "Tier readiness"]) {
      expect(subsystemRowText(name)).toMatch(/not reported.*could not verify/i);
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

  // DG-111: the backend's own disclaimer (a field this endpoint publishes) is
  // still rendered verbatim. Our stamped line beside it, repeated from every
  // other surface, is retired.
  it("renders the backend's exact disclaimer in accessible text, with no added stamp", async () => {
    await renderCard(healthResponse());

    await screen.findByText(DISCLAIMER);
    expect(screen.queryByText("Descriptive only — not decision-grade.")).toBeNull();
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
