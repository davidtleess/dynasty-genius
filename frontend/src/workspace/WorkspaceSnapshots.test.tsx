// @vitest-environment jsdom
// DG-191 — saving what this screen showed, and listing what has been saved.
//
// The behaviours that matter are the honest ones: a duplicate save is not a second observation, a
// save that lands after the sources moved must not describe the new screen as saved, and nothing
// here ever claims a snapshot has been graded.
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { auditRenderedCopy, formatRawCopyFindings } from "../lib/renderRule";
import {
  type SnapshotExpected,
  SnapshotHistory,
  SnapshotSaveControl,
  WorkspaceSnapshotProvider,
} from "./WorkspaceSnapshots";

const EXPECTED: SnapshotExpected = {
  report_run: "20260906T214512Z",
  report_sha256: "19e032a4067dff1759199a84720c0f879bb61f792fd3b2703808b55485a7af37",
  market_sha256: "05bce6dd9d76198ecca2a2f0f1493b4e99f02da1f4dd9a5c1b5b85ec8e01a339",
  league_sha256: "ece82e24a66d50882345733971a8e1c66d1c0bae020496c2f48a8ff8a8ad8a35",
  catalog_run: "20260907T013635Z",
  catalog_content_sha256:
    "d08e89087c5038439d81421cfacba186ebedd4619be9d0015a9c42b74938597e",
};
const MOVED: SnapshotExpected = { ...EXPECTED, market_sha256: "0000000000000000" };

function receipt(over: Record<string, unknown> = {}) {
  return {
    snapshot_id: "a".repeat(64),
    saved_at: "2026-09-08T01:30:00+00:00",
    forecast_date: "2026-09-06",
    market_as_of: "2026-09-06T13:00:02.542329+00:00",
    ownership_as_of: "2026-09-06T13:00:52.635970+00:00",
    years: [2026, 2027, 2028, 2029, 2030],
    source: { ...EXPECTED },
    report_generated_at: "2026-09-06T21:45:12+00:00",
    catalog_generated_at: "2026-09-07T01:36:35+00:00",
    counts: {
      model: 825,
      market: 399,
      market_picks: 24,
      paired: 388,
      roster: 27,
      available: 433,
      available_total: 510,
      available_with_forecasts: 360,
      available_without_forecasts: 73,
      starting_estimates: 7,
    },
    evaluation_plan: { version: 1, target: "season_points" },
    capture_code_sha: "a85f726f23cad759d17877ce2762f93b30d9294f",
    evaluation_status: "ungraded",
    ...over,
  };
}

type Reply = { ok: boolean; status: number; body: unknown };
const ok = (body: unknown): Reply => ({ ok: true, status: 200, body });

/** Routes GET and POST separately so a test can move the server underneath a pending save. */
function mockApi(routes: { get?: () => Reply; post?: () => Promise<Reply> | Reply }) {
  const calls: { method: string; body: unknown }[] = [];
  const fetchMock = vi.fn(
    async (_url: string, init?: { method?: string; body?: string }) => {
      const method = init?.method ?? "GET";
      calls.push({ method, body: init?.body ? JSON.parse(init.body) : null });
      const reply =
        method === "POST"
          ? await (
              routes.post ??
              (() => ok({ status: "saved", created: true, snapshot: receipt() }))
            )()
          : (routes.get ?? (() => ok({ status: "available", snapshots: [] })))();
      return {
        ok: reply.ok,
        status: reply.status,
        json: async () => reply.body,
      };
    },
  );
  vi.stubGlobal("fetch", fetchMock);
  return { fetchMock, calls };
}

function Screen({ expected }: { expected: SnapshotExpected | null }) {
  return (
    <WorkspaceSnapshotProvider expected={expected}>
      <SnapshotSaveControl />
      <SnapshotHistory />
    </WorkspaceSnapshotProvider>
  );
}

const saveButton = () =>
  screen.getByRole("button", {
    name: /Save this snapshot|Saving/,
  }) as HTMLButtonElement;
const history = () => screen.getByRole("region", { name: "Saved snapshots" });

afterEach(() => vi.restoreAllMocks());

describe("saving this screen", () => {
  it("sends the exact source tuple the browser is showing, and says what was archived", async () => {
    const { calls } = mockApi({
      get: () => ok({ status: "available", snapshots: [] }),
      post: () => ok({ status: "saved", created: true, snapshot: receipt() }),
    });
    render(<Screen expected={EXPECTED} />);
    await waitFor(() => expect(saveButton().disabled).toBe(false));
    fireEvent.click(saveButton());
    await waitFor(() =>
      expect(
        screen.getByText(
          "Saved. The forecasts and prices on this screen are archived as they are now.",
        ),
      ).toBeTruthy(),
    );
    const post = calls.find((c) => c.method === "POST");
    expect(post?.body).toEqual({ expected: EXPECTED });
    // the list is re-read so the new snapshot appears, but nothing polls on its own
    expect(calls.filter((c) => c.method === "GET")).toHaveLength(2);
  });

  it("calls a repeat save already saved, keeping the first saved time and adding no observation", async () => {
    mockApi({
      get: () => ok({ status: "available", snapshots: [receipt()] }),
      post: () =>
        ok({
          status: "saved",
          created: false,
          snapshot: receipt({ saved_at: "2026-09-08T01:30:00+00:00" }),
        }),
    });
    render(<Screen expected={EXPECTED} />);
    await waitFor(() => expect(saveButton().disabled).toBe(false));
    fireEvent.click(saveButton());
    await waitFor(() =>
      expect(
        screen.getByText("These forecasts were already saved Sep 8, 2026, 01:30 UTC."),
      ).toBeTruthy(),
    );
    // it is the FORECASTS that were already saved, not this exact rendering of them
    expect(screen.queryByText(/^Saved\./)).toBeNull();
    expect(screen.queryByText("Already saved.")).toBeNull();
    // one archived entry, not two
    expect(within(history()).getAllByRole("listitem")).toHaveLength(1);
  });

  it("says nothing was archived when the server's sources moved first", async () => {
    mockApi({
      post: () => ({ ok: false, status: 409, body: { detail: "sources changed" } }),
    });
    render(<Screen expected={EXPECTED} />);
    await waitFor(() => expect(saveButton().disabled).toBe(false));
    fireEvent.click(saveButton());
    await waitFor(() =>
      expect(
        screen.getByText(
          "The underlying data changed before this could be saved, so no new snapshot was saved by this request. Reload to see the current screen, then save again.",
        ),
      ).toBeTruthy(),
    );
  });

  it("admits it cannot confirm a failed save, rather than claiming nothing was archived", async () => {
    // A connection can fail AFTER the server has written the snapshot, so "nothing was archived"
    // is a fact this path does not have. Retrying is safe because the archive is keyed by content.
    mockApi({ post: () => ({ ok: false, status: 503, body: {} }) });
    render(<Screen expected={EXPECTED} />);
    await waitFor(() => expect(saveButton().disabled).toBe(false));
    fireEvent.click(saveButton());
    await waitFor(() =>
      expect(
        screen.getByText(
          "We could not confirm this save. Try again; saving the same forecasts twice will not duplicate them.",
        ),
      ).toBeTruthy(),
    );
    expect(screen.queryByText(/nothing was archived/)).toBeNull();
  });

  it("refuses to claim success when the receipt is for different sources", async () => {
    mockApi({
      post: () =>
        ok({
          status: "saved",
          created: true,
          snapshot: receipt({
            source: { ...EXPECTED, report_run: "20260905T000000Z" },
          }),
        }),
    });
    render(<Screen expected={EXPECTED} />);
    await waitFor(() => expect(saveButton().disabled).toBe(false));
    fireEvent.click(saveButton());
    await waitFor(() =>
      expect(
        screen.getByText(
          "We could not confirm this save. Try again; saving the same forecasts twice will not duplicate them.",
        ),
      ).toBeTruthy(),
    );
    expect(screen.queryByText(/are archived as they are now/)).toBeNull();
  });

  it("cannot be pressed while a save is in flight", async () => {
    let release: (r: Reply) => void = () => {};
    mockApi({
      post: () =>
        new Promise<Reply>((resolve) => {
          release = resolve;
        }),
    });
    render(<Screen expected={EXPECTED} />);
    await waitFor(() => expect(saveButton().disabled).toBe(false));
    fireEvent.click(saveButton());
    await waitFor(() => expect(saveButton().disabled).toBe(true));
    release(ok({ status: "saved", created: true, snapshot: receipt() }));
    await waitFor(() => expect(saveButton().disabled).toBe(false));
  });
});

describe("when the screen moves under the save", () => {
  it("does not describe the new screen as saved, but still refreshes what is archived", async () => {
    let release: (r: Reply) => void = () => {};
    const { calls } = mockApi({
      get: () => ok({ status: "available", snapshots: [receipt()] }),
      post: () =>
        new Promise<Reply>((resolve) => {
          release = resolve;
        }),
    });
    const { rerender } = render(<Screen expected={EXPECTED} />);
    await waitFor(() => expect(saveButton().disabled).toBe(false));
    fireEvent.click(saveButton());
    // the sources change while the request is still in flight
    rerender(<Screen expected={MOVED} />);
    release(ok({ status: "saved", created: true, snapshot: receipt() }));
    await waitFor(() =>
      expect(calls.filter((c) => c.method === "GET")).toHaveLength(2),
    );
    expect(screen.queryByText(/are archived as they are now/)).toBeNull();
    expect(screen.queryByText("Already saved.")).toBeNull();
  });

  it("clears an earlier success once the screen is showing different sources", async () => {
    mockApi({
      post: () => ok({ status: "saved", created: true, snapshot: receipt() }),
    });
    const { rerender } = render(<Screen expected={EXPECTED} />);
    await waitFor(() => expect(saveButton().disabled).toBe(false));
    fireEvent.click(saveButton());
    await waitFor(() =>
      expect(screen.getByText(/are archived as they are now/)).toBeTruthy(),
    );
    rerender(<Screen expected={MOVED} />);
    expect(screen.queryByText(/are archived as they are now/)).toBeNull();
  });
});

describe("when there is nothing to save", () => {
  it("explains itself and stays disabled with no source details", async () => {
    mockApi({});
    render(<Screen expected={null} />);
    await waitFor(() => expect(saveButton().disabled).toBe(true));
    expect(
      screen.getByText(
        "Source details are not available yet, so there is nothing to save.",
      ),
    ).toBeTruthy();
  });

  it("says saving is switched off rather than failing when the archive is unconfigured", async () => {
    mockApi({ get: () => ok({ status: "not_configured" }) });
    render(<Screen expected={EXPECTED} />);
    await waitFor(() =>
      expect(
        screen.getByText("Saving snapshots is switched off in this setup."),
      ).toBeTruthy(),
    );
    expect(saveButton().disabled).toBe(true);
  });

  it("keeps an unreadable archive visible as unavailable rather than as empty", async () => {
    mockApi({ get: () => ({ ok: false, status: 503, body: {} }) });
    render(<Screen expected={EXPECTED} />);
    await waitFor(() =>
      expect(
        within(history()).getByText(
          "Saved snapshots could not be read. Reload to try again.",
        ),
      ).toBeTruthy(),
    );
    expect(
      within(history()).queryByText("No snapshots have been saved yet."),
    ).toBeNull();
  });
});

describe("what the archive shows", () => {
  it("separates when it was archived from the dates of the data, and counts what is in it", async () => {
    mockApi({ get: () => ok({ status: "available", snapshots: [receipt()] }) });
    render(<Screen expected={EXPECTED} />);
    const entry = await waitFor(() => within(history()).getByRole("listitem"));
    // archived-when and the dates of the data are separate elements, not one merged line
    expect(
      entry.querySelector(".dg-workspace-snapshots__archived")?.textContent,
    ).toMatch(/^Archived Sep 8, 2026/);
    expect(entry.querySelector(".dg-workspace-snapshots__dates")?.textContent).toMatch(
      /Forecasts dated Sep 6, 2026 · Market prices Sep 6, 2026/,
    );
    expect(
      within(entry).getByText(
        /27 of your players · 433 relevant available players, 360 with forecasts and 73 without · 7 starting estimates · 388 ranked on both sides/,
      ),
    ).toBeTruthy();
    expect(within(entry).getByText("Not graded yet.")).toBeTruthy();
  });

  it("says the archive is empty when it is", async () => {
    mockApi({ get: () => ok({ status: "available", snapshots: [] }) });
    render(<Screen expected={EXPECTED} />);
    await waitFor(() =>
      expect(
        within(history()).getByText("No snapshots have been saved yet."),
      ).toBeTruthy(),
    );
  });

  it("never claims a snapshot proves anything", async () => {
    mockApi({ get: () => ok({ status: "available", snapshots: [receipt()] }) });
    const { container } = render(<Screen expected={EXPECTED} />);
    await waitFor(() => within(history()).getByRole("listitem"));
    expect(
      screen.getByText(
        "A snapshot records what this screen showed. It is not a claim that the numbers were frozen on the forecast date, and nothing here has been graded.",
      ),
    ).toBeTruthy();
    const text = (container.textContent ?? "").toLowerCase();
    for (const forbidden of [
      "accurate",
      "edge",
      "beat the market",
      "proven",
      "validated",
    ]) {
      expect(text).not.toContain(forbidden);
    }
  });
});

describe("the amended receipt", () => {
  it("separates when the sources were created from the nominal forecast date", async () => {
    mockApi({ get: () => ok({ status: "available", snapshots: [receipt()] }) });
    render(<Screen expected={EXPECTED} />);
    const entry = await waitFor(() => within(history()).getByRole("listitem"));
    expect(
      entry.querySelector(".dg-workspace-snapshots__created")?.textContent,
    ).toMatch(
      /Report created Sep 6, 2026, 21:45 UTC · Catalog created Sep 7, 2026, 01:36 UTC/,
    );
    // the nominal forecast date stays its own separate line
    expect(entry.querySelector(".dg-workspace-snapshots__dates")?.textContent).toMatch(
      /Forecasts dated Sep 6, 2026/,
    );
  });

  it("says nothing about creation times the source did not carry", async () => {
    mockApi({
      get: () =>
        ok({
          status: "available",
          snapshots: [
            receipt({ report_generated_at: null, catalog_generated_at: null }),
          ],
        }),
    });
    render(<Screen expected={EXPECTED} />);
    const entry = await waitFor(() => within(history()).getByRole("listitem"));
    expect(entry.querySelector(".dg-workspace-snapshots__created")).toBeNull();
    expect(entry.textContent).not.toContain("created");
  });

  it("keeps market players, market picks and the whole catalog apart from the relevant pool", async () => {
    mockApi({ get: () => ok({ status: "available", snapshots: [receipt()] }) });
    render(<Screen expected={EXPECTED} />);
    const entry = await waitFor(() => within(history()).getByRole("listitem"));
    fireEvent.click(within(entry).getByText("More counts"));
    expect(
      within(entry).getByText(
        /825 players we forecast · 399 market players and 24 market picks · 510 catalog rows in total, of which 433 are the relevant pool/,
      ),
    ).toBeTruthy();
  });

  it("never presents the archive as a number of independent observations", async () => {
    mockApi({
      get: () =>
        ok({
          status: "available",
          snapshots: [receipt(), receipt({ snapshot_id: "b".repeat(64) })],
        }),
    });
    const { container } = render(<Screen expected={EXPECTED} />);
    await waitFor(() =>
      expect(within(history()).getAllByRole("listitem")).toHaveLength(2),
    );
    const text = (container.textContent ?? "").toLowerCase();
    for (const forbidden of ["2 snapshots", "observations", "samples", "predictions"]) {
      expect(text).not.toContain(forbidden);
    }
  });
});

describe("already-saved sources", () => {
  it("recognises a source tuple already in the archive before anything is pressed", async () => {
    mockApi({ get: () => ok({ status: "available", snapshots: [receipt()] }) });
    render(<Screen expected={EXPECTED} />);
    await waitFor(() =>
      expect(
        screen.getByText("These forecasts were already saved Sep 8, 2026, 01:30 UTC."),
      ).toBeTruthy(),
    );
    // saving again stays possible; it is simply not a new observation
    expect(saveButton().disabled).toBe(false);
  });

  it("reports the earliest saved time when the same sources were archived more than once", async () => {
    // The capture tool can archive a second rendering of the same sources; that is not a second
    // forecast, so the date shown is the first time these forecasts were saved.
    mockApi({
      get: () =>
        ok({
          status: "available",
          snapshots: [
            receipt({
              snapshot_id: "c".repeat(64),
              saved_at: "2026-09-08T04:00:00+00:00",
            }),
            receipt({
              snapshot_id: "d".repeat(64),
              saved_at: "2026-09-08T01:30:00+00:00",
            }),
          ],
        }),
    });
    render(<Screen expected={EXPECTED} />);
    await waitFor(() =>
      expect(
        screen.getByText("These forecasts were already saved Sep 8, 2026, 01:30 UTC."),
      ).toBeTruthy(),
    );
  });

  it("says nothing of the sort when the archive holds a different source tuple", async () => {
    mockApi({
      get: () =>
        ok({
          status: "available",
          snapshots: [
            receipt({ source: { ...EXPECTED, report_run: "20260905T000000Z" } }),
          ],
        }),
    });
    render(<Screen expected={EXPECTED} />);
    await waitFor(() => expect(within(history()).getByRole("listitem")).toBeTruthy());
    expect(screen.queryByText(/were already saved/)).toBeNull();
  });
});

describe("what must never reach the screen", () => {
  it("shows no hash, snapshot id, code identity, path or endpoint name", async () => {
    mockApi({ get: () => ok({ status: "available", snapshots: [receipt()] }) });
    const { container } = render(<Screen expected={EXPECTED} />);
    await waitFor(() => within(history()).getByRole("listitem"));
    const text = container.textContent ?? "";
    for (const secret of [
      "a".repeat(64),
      EXPECTED.report_sha256,
      EXPECTED.market_sha256,
      EXPECTED.league_sha256,
      EXPECTED.catalog_content_sha256,
      EXPECTED.report_run,
      EXPECTED.catalog_run,
      "a85f726f",
      "/api/research/snapshots",
    ]) {
      expect(text).not.toContain(secret);
    }
  });

  it("puts no raw pipeline key or shouted token on screen", async () => {
    mockApi({ get: () => ok({ status: "available", snapshots: [receipt()] }) });
    const { container } = render(<Screen expected={EXPECTED} />);
    await waitFor(() => within(history()).getByRole("listitem"));
    const findings = auditRenderedCopy(container);
    expect(findings, formatRawCopyFindings(findings)).toEqual([]);
  });

  it("refuses a receipt that does not match the contract rather than rendering half of it", async () => {
    mockApi({
      get: () =>
        ok({
          status: "available",
          snapshots: [receipt({ evaluation_status: "graded" })],
        }),
    });
    render(<Screen expected={EXPECTED} />);
    await waitFor(() =>
      expect(
        within(history()).getByText(
          "Saved snapshots could not be read. Reload to try again.",
        ),
      ).toBeTruthy(),
    );
  });
});

describe("operating it", () => {
  it("is a real button with a reachable explanation, not a custom control", async () => {
    mockApi({ get: () => ok({ status: "available", snapshots: [] }) });
    render(<Screen expected={EXPECTED} />);
    await waitFor(() => expect(saveButton().disabled).toBe(false));
    expect(saveButton().tagName).toBe("BUTTON");
    expect(saveButton().getAttribute("type")).toBe("button");
    expect(screen.getByRole("status")).toBeTruthy();
  });
});

it("keeps saving reachable from history after the first snapshot", async () => {
  mockApi({ get: () => ok({ status: "available", snapshots: [receipt()] }) });
  render(
    <WorkspaceSnapshotProvider expected={EXPECTED}>
      <SnapshotHistory action={<SnapshotSaveControl />} />
    </WorkspaceSnapshotProvider>,
  );
  await within(history()).findByText("Not graded yet.");
  expect(
    within(history()).getByRole("button", { name: "Save this snapshot" }),
  ).toBeTruthy();
});
