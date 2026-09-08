// DG-203 — roster → player → same-position alternative → an explicit comparison of both players.
//
// Both selected players live in the URL, so the pair is shareable and neither is implied. The product
// never nominates a replacement: an alternative is only ever offered, and a comparison happens because
// two ids were chosen. Fields the accepted source does not carry (age, draft year, tier, worth margin)
// are gone rather than guessed.
//
// The panel is a native <dialog> opened with showModal(). That is what buys real modal behaviour with
// no dependency: focus containment, Escape, focus returned to the row that opened it, and the rest of
// the page made inert. A div with a backdrop class looks the same and does none of it.
//
// Every hook runs before any conditional return, so the hook order cannot change between renders.
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useRouterState } from "@tanstack/react-router";

import { say } from "@/lib/dg/copy";
import { forecastLabels, gapLabel, rankLabel, type BoardRow } from "@/lib/dg/backend";
import { playerQuery } from "@/lib/dg/queries";
import { AdvantageCell, GapCell, Headshot, PointsCell, PriceCell, RankPair } from "./Cells";
import { CohortChart } from "./CohortChart";
import { ReceiptSheet } from "./ReceiptSheet";

export function PlayerDrawer() {
  const navigate = useNavigate();
  const search = useRouterState({ select: (s) => s.location.search as Record<string, unknown> });
  const playerId = typeof search["player"] === "string" ? (search["player"] as string) : null;
  const compareId = typeof search["compare"] === "string" ? (search["compare"] as string) : null;

  const player = useQuery(playerQuery(playerId));
  const other = useQuery(playerQuery(compareId));
  const dialogRef = useRef<HTMLDialogElement>(null);
  const openRef = useRef(false);
  const isOpen = playerId !== null;
  openRef.current = isOpen;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (isOpen && !dialog.open) dialog.showModal();
    if (!isOpen && dialog.open) dialog.close();
  }, [isOpen]);

  // showModal makes the rest of the page inert, but the document behind it still scrolls.
  useEffect(() => {
    if (!isOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [isOpen]);

  const close = () => navigate({ to: ".", search: () => ({}) });
  const clearCompare = () =>
    navigate({ to: ".", search: () => (playerId ? { player: playerId } : {}) });
  const chooseCompare = (id: string) =>
    navigate({ to: ".", search: (prev: Record<string, unknown>) => ({ ...prev, compare: id }) });

  const data = player.data ?? null;
  const row = data?.current ?? null;
  const labels = forecastLabels(data?.basis.years ?? []);

  return (
    <dialog
      ref={dialogRef}
      className="dg-drawer border-l bg-[var(--surface)] p-5"
      aria-label={row ? `${row.full_name}, player detail` : "Player detail"}
      style={{
        marginLeft: "auto",
        marginRight: 0,
        marginTop: 0,
        marginBottom: 0,
        height: "100%",
        maxHeight: "100%",
        width: "100%",
        maxWidth: 560,
        overflow: "auto",
        border: 0,
        borderLeft: "1px solid var(--hairline)",
      }}
      onCancel={(event) => {
        event.preventDefault();
        close();
      }}
      onClose={() => {
        if (openRef.current) close();
      }}
    >
      {!isOpen ? null : (
        <>
          <div className="flex items-start justify-between gap-4">
            <div className="flex min-w-0 items-center gap-3">
              {row ? <Headshot row={row} size={44} /> : null}
              <div className="min-w-0">
                <p className="truncate text-[19px] font-bold leading-tight">
                  {row?.full_name ?? "Player"}
                </p>
                {row ? (
                  <>
                    <p className="label-caps mt-1">
                      {row.position ? say(row.position) : "—"}
                      {row.team ? ` · ${row.team}` : ""}
                      {row.status ? ` · ${say(row.status)}` : ""}
                    </p>
                    <p className="label-caps mt-0.5">{row.ownership}</p>
                  </>
                ) : null}
              </div>
            </div>
            <button
              type="button"
              className="label-caps"
              onClick={close}
              aria-label="Close player detail"
              style={{ minHeight: 44 }}
            >
              Close
            </button>
          </div>

          {player.isError ? (
            <p role="alert" className="mt-6 text-sm text-[var(--ink-dim)]">
              His saved card could not be loaded.
            </p>
          ) : player.isPending ? (
            <p role="status" className="mt-6 text-sm text-[var(--ink-dim)]">
              Opening his card…
            </p>
          ) : !row ? (
            <p className="mt-6 text-sm text-[var(--ink-dim)]">
              This player is not in the saved snapshot.
            </p>
          ) : (
            <>
              <div className="mt-5 grid grid-cols-2 gap-3">
                <Panel label="Rank, ours and the market's">
                  <RankPair ours={row.our_rank} market={row.market_rank} />
                </Panel>
                <Panel label="Rank difference">
                  <GapCell row={row} />
                </Panel>
                <Panel label="Our advantage">
                  <AdvantageCell row={row} />
                </Panel>
                <Panel label="Market price">
                  <PriceCell row={row} />
                </Panel>
                <Panel label={labels.current}>
                  <PointsCell value={row.now_points} startingEstimate={row.starting_estimate} />
                </Panel>
                <Panel label={labels.future}>
                  <PointsCell value={row.future_points} startingEstimate={row.starting_estimate} />
                </Panel>
              </div>

              {row.model_zero_tie || other.data?.current?.model_zero_tie ? (
                <p className="mt-3 text-sm text-[var(--ink-dim)]">
                  Zero is a floor: negative projected advantages are set to zero. Players at this
                  floor share a tied value; it does not mean they are forecast to score exactly at
                  replacement.
                </p>
              ) : null}

              <CohortChart ours={row.our_rank} market={row.market_rank} />

              {compareId === null ? null : other.isError ? (
                <p role="alert" className="mt-5 text-sm text-[var(--ink-dim)]">
                  The second player could not be loaded, so no comparison is shown.{" "}
                  <button type="button" className="label-caps underline" onClick={clearCompare}>
                    Clear
                  </button>
                </p>
              ) : other.isPending ? (
                <p role="status" className="mt-5 text-sm text-[var(--ink-dim)]">
                  Opening the second player…
                </p>
              ) : !other.data?.current ? (
                <p className="mt-5 text-sm text-[var(--ink-dim)]">
                  This player is not in the saved snapshot.{" "}
                  <button type="button" className="label-caps underline" onClick={clearCompare}>
                    Clear
                  </button>
                </p>
              ) : (
                <Comparison
                  mine={row}
                  rival={other.data.current}
                  onClear={clearCompare}
                  labels={labels}
                />
              )}

              <Alternatives
                position={row.position}
                rows={data?.alternatives ?? []}
                selectedId={compareId}
                onCompare={chooseCompare}
              />

              {data ? <ReceiptSheet row={row} basis={data.basis} snapshot={data.snapshot} /> : null}
            </>
          )}
        </>
      )}
    </dialog>
  );
}

function Panel({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-md border p-3" style={{ borderColor: "var(--hairline)" }}>
      <p className="label-caps">{label}</p>
      <div className="mt-1">{children}</div>
    </div>
  );
}

/** Same position, unowned, inside the default population. Offered, never recommended. */
function Alternatives({
  position,
  rows,
  selectedId,
  onCompare,
}: {
  position: string | null;
  rows: BoardRow[];
  selectedId: string | null;
  onCompare: (id: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [shown, setShown] = useState(25);
  const needle = query.trim().toLocaleLowerCase();
  const matching = needle
    ? rows.filter((r) => r.full_name.toLocaleLowerCase().includes(needle))
    : rows;
  const visible = matching.slice(0, shown);

  return (
    <section className="mt-5">
      <h3 className="text-[13px] font-semibold tracking-tight">
        Unowned {position ?? "players"} you could compare him with
      </h3>
      <p className="label-caps mt-1">
        {rows.length} available in this saved reading · ordered by this season&rsquo;s points,
        missing readings last · this order is not a pickup recommendation
      </p>

      <label className="label-caps mt-3 flex items-center gap-2">
        Find one
        <input
          type="search"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setShown(25);
          }}
          placeholder="Player name"
          className="flex-1 rounded-sm border bg-transparent px-2 py-1 text-[13px]"
          style={{ borderColor: "var(--hairline)", minHeight: 44 }}
        />
      </label>

      {matching.length === 0 ? (
        <p className="mt-3 text-sm text-[var(--ink-dim)]">
          {rows.length === 0
            ? "Nobody unowned at this position in this reading."
            : "No unowned player at this position matches that name."}
        </p>
      ) : (
        <>
          <ul className="mt-3 space-y-1">
            {visible.map((alt) => (
              <li key={alt.player_id}>
                <div
                  className="row-grid items-center"
                  style={{ gridTemplateColumns: "1fr auto auto", gap: "0 10px", minHeight: 44 }}
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <Headshot row={alt} />
                    <span className="min-w-0">
                      <span className="block truncate text-[13px] font-semibold">
                        {alt.full_name}
                      </span>
                      <span className="label-caps">
                        Ours {rankLabel(alt.our_rank)} · market {rankLabel(alt.market_rank)}
                      </span>
                    </span>
                  </span>
                  <PointsCell value={alt.now_points} startingEstimate={alt.starting_estimate} />
                  <button
                    type="button"
                    className="label-caps rounded-sm border px-2 py-1"
                    style={{
                      borderColor:
                        alt.player_id === selectedId ? "var(--primary)" : "var(--hairline)",
                      minHeight: 44,
                    }}
                    onClick={() => onCompare(alt.player_id)}
                    aria-pressed={alt.player_id === selectedId}
                    aria-label={`Compare ${alt.full_name} with this player`}
                  >
                    {alt.player_id === selectedId ? "Comparing" : "Compare"}
                  </button>
                </div>
              </li>
            ))}
          </ul>
          <p className="label-caps mt-2">
            Showing {visible.length} of {matching.length}
            {needle ? ` matching “${query.trim()}”` : ""}.
          </p>
          {visible.length < matching.length ? (
            <button
              type="button"
              className="label-caps mt-2 rounded-sm border px-2 py-1"
              style={{ borderColor: "var(--hairline)", minHeight: 44 }}
              onClick={() => setShown((n) => n + 25)}
            >
              Show 25 more
            </button>
          ) : null}
        </>
      )}
    </section>
  );
}

/** Two players, both chosen explicitly. Each reading keeps its own row and its own units. */
function Comparison({
  mine,
  rival,
  onClear,
  labels,
}: {
  mine: BoardRow;
  rival: BoardRow;
  onClear: () => void;
  labels: { current: string; future: string };
}) {
  const rows: [string, (r: BoardRow) => React.ReactNode][] = [
    ["Our rank", (r) => <span className="num text-[13px]">{rankLabel(r.our_rank)}</span>],
    ["Market rank", (r) => <span className="num text-[13px]">{rankLabel(r.market_rank)}</span>],
    ["Rank difference", (r) => <span className="text-[13px]">{gapLabel(r)}</span>],
    ["Our advantage", (r) => <AdvantageCell row={r} />],
    ["Market price", (r) => <PriceCell row={r} />],
    [
      labels.current,
      (r) => <PointsCell value={r.now_points} startingEstimate={r.starting_estimate} />,
    ],
    [
      labels.future,
      (r) => <PointsCell value={r.future_points} startingEstimate={r.starting_estimate} />,
    ],
    ["Ownership", (r) => <span className="label-caps">{r.ownership}</span>],
  ];
  return (
    <section className="mt-5" aria-label={`${mine.full_name} compared with ${rival.full_name}`}>
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="text-[13px] font-semibold tracking-tight">
          {mine.full_name} and {rival.full_name}
        </h3>
        <button
          type="button"
          className="label-caps"
          onClick={onClear}
          aria-label="Clear the comparison"
        >
          Clear
        </button>
      </div>
      <p className="label-caps mt-1">
        Both players chosen by you. Each reading keeps its own row; nothing here is subtracted
        across units.
      </p>
      <div className="mt-3 space-y-1">
        <div
          className="row-grid label-caps"
          style={{ gridTemplateColumns: "1.1fr 1fr 1fr", gap: "0 10px" }}
        >
          <span />
          <span className="truncate">{mine.full_name}</span>
          <span className="truncate">{rival.full_name}</span>
        </div>
        {rows.map(([label, render]) => (
          <div
            key={label}
            className="row-grid items-baseline"
            style={{ gridTemplateColumns: "1.1fr 1fr 1fr", gap: "0 10px" }}
          >
            <span className="label-caps">{label}</span>
            {render(mine)}
            {render(rival)}
          </div>
        ))}
      </div>
    </section>
  );
}
