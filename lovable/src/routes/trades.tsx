import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { AppShell } from "@/components/dg/AppShell";
import { Headshot } from "@/components/dg/Cells";
import { Command, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { boardQuery } from "@/lib/dg/queries";
import { rankLabel, type BoardRow } from "@/lib/dg/backend";
import { validatePlayerSearch } from "@/lib/dg/search";

export const Route = createFileRoute("/trades")({
  validateSearch: validatePlayerSearch,
  head: () => ({ meta: [{ title: "Player compare — Dynasty Genius" }] }),
  component: PlayerCompare,
});
function PlayerCompare() {
  const { data, isPending, isError } = useQuery(boardQuery("universe"));
  const search = Route.useSearch();
  const navigate = useNavigate();
  const [first, setFirst] = useState<string | null>(search.player ?? null);
  const [second, setSecond] = useState<string | null>(search.compare ?? null);
  const a = data?.find((r) => r.player_id === first);
  const b = data?.find((r) => r.player_id === second);
  return (
    <AppShell title="Player compare">
      <p className="text-[18px] font-semibold">Two players. Our view and the market's.</p>
      <p className="mt-2 text-sm text-[var(--ink-dim)]">
        Choose both sides to compare their ranks, FantasyCalc prices and available season forecasts.
      </p>
      {isError ? (
        <p role="alert" className="mt-5">
          Players could not load. Reload the current board to try again.
        </p>
      ) : isPending ? (
        <p role="status" className="mt-5">
          Opening the player list…
        </p>
      ) : (
        <>
          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            <PlayerChoice
              label="First player"
              rows={data ?? []}
              chosen={a}
              excluded={second}
              onChoose={setFirst}
            />
            <PlayerChoice
              label="Second player"
              rows={data ?? []}
              chosen={b}
              excluded={first}
              onChoose={setSecond}
            />
          </div>
          <button
            type="button"
            disabled={!a || !b || first === second}
            className="mt-5 min-h-11 rounded border bg-[var(--foreground)] px-5 text-sm font-semibold text-[var(--background)] disabled:opacity-40"
            onClick={() => {
              if (a && b && a.player_id !== b.player_id)
                navigate({
                  to: ".",
                  search: (previous: Record<string, unknown>) => ({
                    ...previous,
                    player: a.player_id,
                    compare: b.player_id,
                  }),
                });
            }}
          >
            Compare players
          </button>
          {!a || !b ? (
            <p className="mt-2 text-[12px] text-[var(--ink-dim)]">
              Select two different players to open their comparison.
            </p>
          ) : null}
        </>
      )}
      <p className="mt-6 text-[12px] text-[var(--ink-dim)]">
        A player comparison helps explore a trade or roster choice. It does not price draft picks,
        account for an entire trade package, or show trade history.
      </p>
    </AppShell>
  );
}
function PlayerChoice({
  label,
  rows,
  chosen,
  excluded,
  onChoose,
}: {
  label: string;
  rows: BoardRow[];
  chosen: BoardRow | undefined;
  excluded: string | null;
  onChoose: (id: string | null) => void;
}) {
  const [term, setTerm] = useState("");
  const matching =
    term.trim().length >= 2
      ? rows.filter(
          (r) =>
            r.player_id !== excluded &&
            r.full_name.toLocaleLowerCase().includes(term.trim().toLocaleLowerCase()),
        )
      : [];
  return (
    <section className="min-w-0 rounded border p-4" aria-label={label}>
      <h2 className="mb-3 font-semibold">{label}</h2>
      {chosen ? (
        <div className="flex items-center gap-3">
          <Headshot row={chosen} size={40} />
          <span className="min-w-0 flex-1">
            <span className="block truncate font-semibold">{chosen.full_name}</span>
            <span className="text-[12px] text-[var(--ink-dim)]">
              {chosen.position} · {chosen.ownership}
            </span>
          </span>
          <button
            type="button"
            className="min-h-11 px-2 text-sm underline"
            onClick={() => {
              onChoose(null);
              setTerm("");
            }}
            aria-label={`Change ${label.toLowerCase()}`}
          >
            Change
          </button>
        </div>
      ) : (
        <Command label={`Find ${label.toLowerCase()}`} shouldFilter={false}>
          <CommandInput
            value={term}
            onValueChange={setTerm}
            aria-label={`Find ${label.toLowerCase()}`}
            placeholder="Search a player…"
          />
          <CommandList className="max-h-72" aria-label={`${label} matches`}>
            {matching.slice(0, 12).map((row) => (
              <CommandItem
                key={row.player_id}
                value={row.player_id}
                className="min-h-14 cursor-pointer gap-2"
                onSelect={() => onChoose(row.player_id)}
              >
                <Headshot row={row} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate">{row.full_name}</span>
                  <span className="block text-[11px] text-[var(--ink-dim)]">
                    {row.position} · {row.ownership}
                  </span>
                </span>
                <span className="text-right text-[11px]">
                  <span className="block" style={{ color: "var(--ours)" }}>
                    Ours {rankLabel(row.our_rank)}
                  </span>
                  <span className="block" style={{ color: "var(--market)" }}>
                    FC {rankLabel(row.market_rank)}
                  </span>
                </span>
              </CommandItem>
            ))}
            <p role="status" className="p-3 text-[12px] text-[var(--ink-dim)]">
              {term.trim().length < 2
                ? "Type two or more letters to search all players."
                : !matching.length
                  ? "No matching player. Try another name."
                  : matching.length > 12
                    ? `${matching.length} matches. Keep typing to narrow the list.`
                    : `${matching.length} matching players.`}
            </p>
          </CommandList>
        </Command>
      )}
    </section>
  );
}
