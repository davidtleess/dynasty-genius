import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { Search } from "lucide-react";

import { Command, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { searchQuery } from "@/lib/dg/queries";
import { rankLabel } from "@/lib/dg/backend";
import { selectPlayerSearch } from "@/lib/dg/polish";
import { Headshot } from "./Cells";

export function PlayerPalette() {
  const [open, setOpen] = useState(false);
  const [term, setTerm] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { data, isFetching, isError } = useQuery(searchQuery(term));
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((value) => !value);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  useEffect(() => {
    if (open && !dialog.current?.open) {
      dialog.current?.showModal();
      input.current?.focus();
    }
    if (!open && dialog.current?.open) dialog.current?.close();
  }, [open]);
  function close() {
    setOpen(false);
    setTerm("");
  }
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="dg-search-trigger"
        aria-label="Find a player"
      >
        <Search size={16} aria-hidden="true" />
        <span>Find a player</span>
        <kbd className="hidden text-[11px] md:inline">⌘ / Ctrl K</kbd>
      </button>
      <dialog
        ref={dialog}
        className="dg-search-dialog"
        aria-labelledby="player-search-title"
        onCancel={(event) => {
          event.preventDefault();
          close();
        }}
        onClose={close}
      >
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h2 id="player-search-title" className="font-semibold">
            Find a player
          </h2>
          <button type="button" onClick={close} className="min-h-11 px-2 text-sm">
            Close
          </button>
        </div>
        <Command label="Player name" shouldFilter={false}>
          <CommandInput
            ref={input}
            value={term}
            onValueChange={setTerm}
            placeholder="Search by player name…"
            aria-label="Player name"
          />
          <CommandList className="max-h-[55dvh] px-2 pb-2" aria-label="Matching players">
            {term.trim().length < 2 ? (
              <p className="p-4 text-sm text-[var(--ink-dim)]">
                Type at least two letters. Search every player on the current board.
              </p>
            ) : isError ? (
              <p role="alert" className="p-4 text-sm">
                Player search could not load. Reload the saved reading to try again.
              </p>
            ) : isFetching ? (
              <p role="status" className="p-4 text-sm">
                Finding players…
              </p>
            ) : !data?.length ? (
              <p role="status" className="p-4 text-sm">
                No players match “{term.trim()}”.
              </p>
            ) : (
              data.map((row) => (
                <CommandItem
                  key={row.player_id}
                  value={row.player_id}
                  className="min-h-16 cursor-pointer gap-3"
                  onSelect={() => {
                    close();
                    navigate({
                      to: ".",
                      search: (previous: Record<string, unknown>) =>
                        selectPlayerSearch(previous, row.player_id),
                    });
                  }}
                >
                  <Headshot row={row} size={36} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-semibold">{row.full_name}</span>
                    <span className="block text-[12px] text-[var(--ink-dim)]">
                      {row.position ?? "—"} · {row.team ?? "No NFL team"} · {row.ownership}
                    </span>
                  </span>
                  <span className="shrink-0 text-right text-[12px]">
                    <span className="block" style={{ color: "var(--ours)" }}>
                      Our rank {rankLabel(row.our_rank)}
                    </span>
                    <span className="block" style={{ color: "var(--market)" }}>
                      Market rank {rankLabel(row.market_rank)}
                    </span>
                  </span>
                </CommandItem>
              ))
            )}
          </CommandList>
        </Command>
      </dialog>
    </>
  );
}
