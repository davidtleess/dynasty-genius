// @vitest-environment jsdom
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProjectTracker } from "./ProjectTracker";

const OK = {
  source: "resources/project_plan.json",
  schema_version: "project_plan.v1",
  updated_at: "2026-06-19",
  parser_version: "v1",
  status: "ok",
  warnings: [],
  phases: [
    {
      id: "p1",
      title: "Phase 1",
      status: "in_progress",
      summary: "s",
      tasks: [{ id: "t1", title: "Task 1", status: "done", note: null }],
    },
  ],
};

function mockFetch(status, body) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: status === 200,
    status,
    json: async () => body,
  });
}

afterEach(() => vi.restoreAllMocks());

describe("ProjectTracker", () => {
  it("renders phases and expands to tasks", async () => {
    mockFetch(200, OK);
    render(<ProjectTracker />);
    await waitFor(() => expect(screen.getByText("Phase 1")).toBeTruthy());
    fireEvent.click(screen.getByText("Phase 1"));
    await waitFor(() => expect(screen.getByText("Task 1")).toBeTruthy());
  });

  it("renders a status badge from the enum", async () => {
    mockFetch(200, OK);
    render(<ProjectTracker />);
    await waitFor(() =>
      expect(screen.getAllByText(/in_progress/i).length).toBeGreaterThan(0),
    );
  });

  it("renders degraded warnings without crashing", async () => {
    mockFetch(200, {
      ...OK,
      status: "degraded",
      phases: [],
      warnings: ["project_plan_source_missing"],
    });
    render(<ProjectTracker />);
    await waitFor(() =>
      expect(screen.getByText(/project_plan_source_missing/i)).toBeTruthy(),
    );
  });

  it("renders an honest error on parse failure", async () => {
    mockFetch(200, { bogus: true });
    render(<ProjectTracker />);
    await waitFor(() =>
      expect(screen.getByText(/could not load the project plan/i)).toBeTruthy(),
    );
  });

  it("refresh re-fetches", async () => {
    mockFetch(200, OK);
    render(<ProjectTracker />);
    await waitFor(() => expect(screen.getByText("Phase 1")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /refresh/i }));
    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledTimes(2));
  });
});
