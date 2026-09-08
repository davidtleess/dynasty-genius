/**
 * The copy dictionary. Backend keys never reach the DOM — they come through
 * here first. If a key is not mapped, we say so in football words rather than
 * printing the key.
 */

const DICTIONARY: Record<string, string> = {
  // slots
  QB: "Quarterback",
  RB: "Running back",
  WR: "Receiver",
  TE: "Tight end",
  bench: "Bench",
  starter: "Starting lineup",
  ir: "Injured reserve",
  taxi: "Taxi squad",

  // lanes
  our_value: "Our worth",
  our_rank: "Our rank",
  market_value: "Market worth",
  market_rank: "Market rank",
  margin: "Margin",
  rank_margin: "Rank margin",

  // transactions
  trade: "Trade",
  waiver: "Waiver claim",
  free_agent: "Free agent move",
  commissioner: "Commissioner move",

  // injury words
  IR: "On injured reserve",
  Out: "Out",
  Questionable: "Questionable",
  Doubtful: "Doubtful",
  Sus: "Suspended",
  PUP: "On the physically unable to perform list",
  NA: "Not available",
};

export function say(key: string | null | undefined, fallback = "Not stated"): string {
  if (!key) return fallback;
  const hit = DICTIONARY[key];
  if (hit) return hit;
  // Never print a raw pipeline key. Turn it into readable words instead.
  const words = key.replace(/[_.-]+/g, " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export const TIERS = ["Generational", "Elite", "Cornerstone", "Starter", "Depth"] as const;
export type Tier = (typeof TIERS)[number];

export const TIER_SHORT: Record<Tier, string> = {
  Generational: "Gen",
  Elite: "Elite",
  Cornerstone: "Corner",
  Starter: "Start",
  Depth: "Depth",
};

/** Reasons a number is absent. Never "evidence incomplete", never a zero. */
export const ABSENCE = {
  noModelScore: "No active model score",
  unmodeled: "Unmodeled category",
  noMarketPrice: "The market has no dynasty price for him",
  noProduction: "No NFL production on file yet",
  noTier: "No tier — the calibration has not earned one for him",
} as const;

export function marginSentence(
  name: string,
  ourValue: number | null,
  marketValue: number | null,
): string {
  if (ourValue == null) return `We carry no worth for ${name}. ${ABSENCE.noModelScore}.`;
  if (marketValue == null)
    return `We carry ${Math.round(ourValue)} on ${name}. ${ABSENCE.noMarketPrice}.`;
  const diff = Math.round(ourValue - marketValue);
  if (diff === 0) return `We and the market land on the same worth for ${name}.`;
  const dir = diff > 0 ? "above" : "below";
  return `We carry ${Math.round(ourValue)} on ${name}; the market carries ${Math.round(
    marketValue,
  )}. We are ${Math.abs(diff)} ${dir} the room.`;
}

export function rankMarginSentence(ourRank: number | null, marketRank: number | null): string {
  if (ourRank == null || marketRank == null) return ABSENCE.noModelScore;
  const gap = marketRank - ourRank;
  if (gap === 0) return "Same rank in both lanes.";
  return gap > 0
    ? `We rank him ${gap} spot${gap === 1 ? "" : "s"} higher than the market does.`
    : `The market ranks him ${Math.abs(gap)} spot${Math.abs(gap) === 1 ? "" : "s"} higher than we do.`;
}

export function freshnessSentence(iso: string | null): string {
  if (!iso) return "No data pull on file yet.";
  const then = new Date(iso).getTime();
  const hours = Math.floor((Date.now() - then) / 36e5);
  if (hours < 1) return "Rosters, market prices and production are current as of the last hour.";
  if (hours < 24)
    return `Rosters, market prices and production last came in ${hours} hour${hours === 1 ? "" : "s"} ago.`;
  const days = Math.floor(hours / 24);
  return `Rosters, market prices and production last came in ${days} day${days === 1 ? "" : "s"} ago.`;
}
