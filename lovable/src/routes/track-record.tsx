// DG-208 — the track record route.
//
// Shared search preserves the selected saved reading through player and comparison navigation.
//
// With no id in the URL the server picks the newest reading deterministically and the browser writes
// that id back, so a refresh returns to the same reading rather than to "whatever is newest now".
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/dg/AppShell";
import { TrackRecordScreen } from "@/components/dg/TrackRecord";
import { validatePlayerSearch, type PlayerSearch } from "@/lib/dg/search";
import { bundleQuery } from "@/lib/dg/queries";
import {
  boardSourceFromBundle,
  saveBoardReading,
  saveEnablement,
  trackRecordQuery,
  TrackRecordError,
} from "@/lib/dg/track-record";

type TrackRecordSearch = PlayerSearch;

/** Invalid selections remain explicit, so they cannot silently become the latest reading. */
function validateTrackRecordSearch(search: Record<string, unknown>): TrackRecordSearch {
  return validatePlayerSearch(search);
}

export const Route = createFileRoute("/track-record")({
  validateSearch: validateTrackRecordSearch,
  head: () => ({
    meta: [
      { title: "Track record — Dynasty Genius" },
      {
        name: "description",
        content: "The readings we have saved, and what each one is waiting to be graded against.",
      },
    ],
  }),
  component: TrackRecordPage,
});

function TrackRecordPage() {
  const navigate = useNavigate();
  const client = useQueryClient();
  const search = Route.useSearch();
  const selectedId = search.snapshot ?? null;
  const [outcome, setOutcome] = useState<string | null>(null);

  const view = useQuery(trackRecordQuery(selectedId));
  const bundle = useQuery(bundleQuery);

  // The server chose a reading; put its id in the URL so a refresh returns to this one.
  const serverSelected = view.data?.selected?.snapshot_id ?? null;
  useEffect(() => {
    if (!selectedId && serverSelected) {
      navigate({
        to: ".",
        search: (previous: Record<string, unknown>) => ({ ...previous, snapshot: serverSelected }),
        replace: true,
      });
    }
  }, [selectedId, serverSelected, navigate]);

  const boardSource = boardSourceFromBundle(bundle.data?.snapshot);
  const capability = view.data?.save_capability ?? { enabled: false, reason: null, expected: null };
  const decision = view.data
    ? bundle.data && !boardSource
      ? {
          enabled: false,
          reason:
            "This board reading is missing source details needed to save it. Reload the board.",
        }
      : saveEnablement(boardSource, capability)
    : { enabled: false, reason: "The archive has not loaded yet." };

  const save = useMutation({
    mutationFn: async () => {
      if (!decision.enabled || !boardSource || !capability.expected)
        throw new TrackRecordError("The archive did not say which reading it expects.");
      return saveBoardReading(capability.expected);
    },
    onSuccess: (result) => {
      // Archiving and enrolling are two outcomes of one deliberate save, and a partial success says so.
      const archived =
        result.snapshot_status === "saved"
          ? "Saved this board reading."
          : "This reading was already saved.";
      const enrolled =
        result.enrollment_status === "saved"
          ? " It is enrolled for evaluation."
          : result.enrollment_status === "already_saved"
            ? " It was already enrolled."
            : ` It was not enrolled. ${result.reason ?? ""}`.trimEnd();
      setOutcome(
        `${archived}${enrolled}${result.enrollment_status !== "input_unavailable" && result.reason ? ` ${result.reason}` : ""}`,
      );
      client.invalidateQueries({ queryKey: ["dg", "track-record"] });
    },
    onError: (error) =>
      setOutcome(
        error instanceof TrackRecordError ? error.message : "The save could not be completed.",
      ),
  });

  return (
    <AppShell title="Track record">
      {view.isPending ? (
        <p role="status" className="mt-4 text-sm text-[var(--ink-dim)]">
          Opening the saved readings…
        </p>
      ) : view.isError ? (
        <section
          className="mt-4 rounded-md border p-4"
          style={{ borderColor: "var(--hairline)" }}
          role="alert"
        >
          <p className="text-sm" style={{ color: "var(--foreground)" }}>
            {selectedId === "invalid"
              ? "That saved-reading link is not valid."
              : "The saved reading could not be opened."}
          </p>
          <p className="mt-2 text-sm text-[var(--ink-dim)]">
            {view.error instanceof TrackRecordError
              ? view.error.message
              : "The request did not complete."}
          </p>
          {selectedId ? (
            <button
              type="button"
              className="mt-3 min-h-11 rounded border px-3 text-sm"
              onClick={() =>
                navigate({
                  to: ".",
                  search: (previous: Record<string, unknown>) => {
                    const next = { ...previous };
                    delete next["snapshot"];
                    return next;
                  },
                })
              }
            >
              Open latest saved reading
            </button>
          ) : null}
        </section>
      ) : (
        <TrackRecordScreen
          view={view.data}
          onSelect={(snapshot) =>
            navigate({
              to: ".",
              search: (previous: Record<string, unknown>) => ({ ...previous, snapshot }),
            })
          }
          onSave={() => save.mutate()}
          saving={save.isPending}
          saveDecision={decision}
          boardDate={bundle.data?.snapshot.forecast_date ?? null}
          saveOutcome={outcome}
        />
      )}
    </AppShell>
  );
}
