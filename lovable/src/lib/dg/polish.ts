type Search = Record<string, unknown>;

export function closePlayerSearch(previous: Search): Search {
  const next = { ...previous };
  delete next["player"];
  delete next["compare"];
  return next;
}

export function selectPlayerSearch(previous: Search, player: string): Search {
  return { ...closePlayerSearch(previous), player };
}

export function clearComparisonSearch(previous: Search): Search {
  const next = { ...previous };
  delete next["compare"];
  return next;
}

export function savedDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Date unavailable"
    : date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        timeZone: "UTC",
      });
}
