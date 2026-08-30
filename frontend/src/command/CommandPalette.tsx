import {
  type KeyboardEvent as ReactKeyboardEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import "./CommandPalette.css";

export type Command = {
  id: string;
  label: string;
  run: () => void;
};

// Hand-rolled subsequence fuzzy match (no cmdk / fuzzy library): every query
// character must appear, in order, somewhere in the label (case-insensitive).
function matchesQuery(label: string, query: string): boolean {
  if (query === "") {
    return true;
  }
  const haystack = label.toLowerCase();
  let cursor = 0;
  for (const char of query.toLowerCase()) {
    cursor = haystack.indexOf(char, cursor);
    if (cursor === -1) {
      return false;
    }
    cursor += 1;
  }
  return true;
}

export function CommandPalette({
  commands,
  extraCommands = [],
  notice,
  onQueryChange,
  placeholder = "Search players and surfaces…",
  open: controlledOpen,
  onOpenChange,
}: {
  commands: Command[];
  /** Already-matched commands (server-side search) — appended unfiltered. */
  extraCommands?: Command[];
  /**
   * A fact about the extra commands that the list itself cannot show — chiefly
   * "the player list could not be read". Without it a failed read renders an
   * empty palette, which reads as "no such player" (DG-110 panel).
   */
  notice?: string | undefined;
  /** DG-110: lets the shell run a live player search on the typed text. */
  onQueryChange?: ((query: string) => void) | undefined;
  placeholder?: string;
  /** Controlled open state; omit to keep the palette's own (⌘K only). */
  open?: boolean | undefined;
  onOpenChange?: ((open: boolean) => void) | undefined;
}) {
  const [uncontrolledOpen, setUncontrolledOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const open = controlledOpen ?? uncontrolledOpen;

  // Both states move together, so a controlled shell and the ⌘K shortcut can
  // never disagree about whether the palette is up.
  function changeOpen(next: boolean): void {
    setUncontrolledOpen(next);
    onOpenChange?.(next);
  }

  function resetQuery(): void {
    setQuery("");
    setActiveIndex(0);
    onQueryChange?.("");
  }

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setUncontrolledOpen(true);
        onOpenChange?.(true);
        setQuery("");
        setActiveIndex(0);
        onQueryChange?.("");
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [onOpenChange, onQueryChange]);

  useEffect(() => {
    if (open) {
      inputRef.current?.focus();
    }
  }, [open]);

  const filtered = useMemo(
    () => [
      ...commands.filter((command) => matchesQuery(command.label, query)),
      ...extraCommands,
    ],
    [commands, extraCommands, query],
  );

  if (!open) {
    return null;
  }

  function handleSearchKeyDown(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      changeOpen(false);
      // Reopening must not restore a stale query and its stale player results;
      // every other close path already resets.
      resetQuery();
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((index) => Math.min(filtered.length - 1, index + 1));
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => Math.max(0, index - 1));
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      const active = filtered[activeIndex];
      if (active) {
        active.run();
        changeOpen(false);
        resetQuery();
      }
    }
  }

  return (
    <div className="dg-cmdk">
      <input
        ref={inputRef}
        type="text"
        className="dg-cmdk__search"
        aria-label="Command palette"
        placeholder={placeholder}
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setActiveIndex(0);
          onQueryChange?.(event.target.value);
        }}
        onKeyDown={handleSearchKeyDown}
      />
      {notice !== undefined && (
        <p className="dg-cmdk__notice" role="status">
          {notice}
        </p>
      )}
      <div className="dg-cmdk__list" role="listbox" aria-label="Commands">
        {filtered.map((command, index) => (
          <button
            key={command.id}
            type="button"
            role="option"
            className="dg-cmdk__option"
            // Arrow keys drive selection from the input's roving index; keeping
            // options out of the tab order stops Tab walking the listbox out
            // from under that model while they stay clickable.
            tabIndex={-1}
            aria-selected={index === activeIndex ? "true" : "false"}
            onClick={() => {
              command.run();
              changeOpen(false);
              resetQuery();
            }}
          >
            {command.label}
          </button>
        ))}
      </div>
    </div>
  );
}
