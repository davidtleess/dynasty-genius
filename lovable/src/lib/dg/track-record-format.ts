import { pointsLabel } from "./backend.ts";

export type Unit = "points" | "places" | "fraction" | "correlation";

export function readingDay(iso: string): string {
  const at = new Date(iso.length <= 10 ? `${iso}T00:00:00Z` : iso);
  return Number.isNaN(at.getTime())
    ? iso
    : at.toLocaleDateString(undefined, {
        day: "numeric",
        month: "short",
        year: "numeric",
        ...(iso.length <= 10 ? { timeZone: "UTC" } : {}),
      });
}

export function resultNumber(value: number | null, unit: Unit = "points"): string {
  if (value === null) return "—";
  if (unit === "points") return pointsLabel(value);
  if (unit === "places") return Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1);
  if (unit === "correlation") return value.toFixed(3);
  const percent = value * 100;
  const digits = Math.abs(percent) >= 10 ? 1 : Math.abs(percent) >= 1 ? 2 : 3;
  return `${Number(percent.toFixed(digits))}%`;
}

export function producerLabel(producer: string | null): string {
  if (!producer) return "—";
  if (/veteran.*annual/i.test(producer)) return "Veteran forecast";
  if (/rookie_capital/i.test(producer)) return "Rookie forecast";
  if (/cold.start/i.test(producer)) return "Starting estimate";
  return /^engine/i.test(producer) ? "Our model" : "Forecast";
}

export function readingText(value: string): string {
  return value
    .replace(/\bREG\b/g, "regular-season")
    .replace(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})/g, (iso) =>
      new Date(iso).toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hourCycle: "h23",
        timeZone: "UTC",
        timeZoneName: "short",
      }),
    );
}

export function missingInputText(value: string | null, omitPriorMarket: boolean): string | null {
  if (!value) return null;
  const parts = value
    .split(";")
    .map((part) => part.trim().replace(/[.]+$/, ""))
    .filter(
      (part) => part && !(omitPriorMarket && part === "no frozen trailing capture was selected"),
    )
    .map((part) =>
      /^(no archived market price|No saved FantasyCalc price for this player)$/i.test(part)
        ? "Market price unavailable"
        : part === "no archived market rank"
          ? "Market rank unavailable"
          : part.charAt(0).toUpperCase() + part.slice(1),
    );
  return parts.length ? [...new Set(parts)].join(". ") + "." : null;
}
