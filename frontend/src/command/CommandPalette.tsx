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

export function CommandPalette({ commands }: { commands: Command[] }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen(true);
        setQuery("");
        setActiveIndex(0);
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  useEffect(() => {
    if (open) {
      inputRef.current?.focus();
    }
  }, [open]);

  const filtered = useMemo(
    () => commands.filter((command) => matchesQuery(command.label, query)),
    [commands, query],
  );

  if (!open) {
    return null;
  }

  function handleSearchKeyDown(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setOpen(false);
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
        setOpen(false);
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
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setActiveIndex(0);
        }}
        onKeyDown={handleSearchKeyDown}
      />
      <div className="dg-cmdk__list" role="listbox" aria-label="Commands">
        {filtered.map((command, index) => (
          <div
            key={command.id}
            role="option"
            tabIndex={-1}
            className="dg-cmdk__option"
            aria-selected={index === activeIndex ? "true" : "false"}
          >
            {command.label}
          </div>
        ))}
      </div>
    </div>
  );
}
