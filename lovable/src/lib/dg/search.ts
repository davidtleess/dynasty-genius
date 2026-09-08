/** Both selected players remain explicit and shareable in the URL. */
export type PlayerSearch = { player?: string; compare?: string };
export function validatePlayerSearch(search: Record<string, unknown>): PlayerSearch {
  const result: PlayerSearch = {};
  for (const key of ["player", "compare"] as const) {
    const value = search[key];
    if (typeof value === "string" && /^\d+$/.test(value)) result[key] = value;
  }
  if (!result.player || result.compare === result.player) delete result.compare;
  return result;
}

/** Keep Sleeper IDs as strings instead of JSON-encoding numeric-looking search values. */
export function parsePlayerSearch(search: string): PlayerSearch {
  const values = Object.fromEntries(new URLSearchParams(search));
  for (const key of ["player", "compare"]) {
    const value = values[key];
    if (value && /^"\d+"$/.test(value)) values[key] = value.slice(1, -1);
  }
  return validatePlayerSearch(values);
}

export function stringifyPlayerSearch(search: Record<string, unknown>): string {
  const values = validatePlayerSearch(search);
  const params = new URLSearchParams();
  if (values.player) params.set("player", values.player);
  if (values.compare) params.set("compare", values.compare);
  const query = params.toString();
  return query ? `?${query}` : "";
}
