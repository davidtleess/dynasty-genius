import { defineConfig } from "../../frontend/node_modules/@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: "dg022-real-surface.spec.ts",
  outputDir: "playwright-output",
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  timeout: 120_000,
  use: {
    baseURL: "http://127.0.0.1:8122",
    browserName: "chromium",
    trace: "retain-on-failure",
  },
});
