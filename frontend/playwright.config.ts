// H2 reset Task 1 — the browser evidence gate (reset spec §6 Task 1).
// LOCAL-FIRST, capture-first: evidence artifacts only. No golden baselines
// (no snapshotPathTemplate / toHaveScreenshot) and no CI hard gate until
// repeated local runs prove the harness stable (capability plan Task 2 rule).
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "visual-smoke.spec.ts",
  outputDir: "./artifacts/visual-output",
  // Evidence must be deterministic-ish and reviewable, not flake-gated:
  // one worker, no retries — a failure is information, not a rerun target.
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:4173",
    // Trace on failure so a broken capture run explains itself.
    trace: "retain-on-failure",
  },
  // Serve the REAL built app via vite preview; the spec supplies route mocks
  // so no gitignored app/data artifact is ever required.
  //
  // DG-118: `reuseExistingServer` was true, which meant that if ANY vite preview
  // was already listening on 4173 — another worktree, another agent, a stale
  // process from an hour ago — this gate would silently grade THAT bundle and
  // write a receipt with this ticket's name on it. A gate that cannot say which
  // build it measured is decoration. Now it always builds and serves its own,
  // and `--strictPort` in the `preview` script makes a busy port a loud failure
  // instead of a quiet substitution.
  webServer: {
    command: "npm run build && npm run preview",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
