export const LEAGUE = {
  id: "1314363401744416768",
  name: "Redzone Champions League",
  season: "2026",
  teams: 12,
  format: "Dynasty · Superflex · full PPR · no tight end premium",
  ownerSleeperUserId: "827345221493850112",
  ownerHandle: "dleess",
  myTeamName: "Woodbury Riders",
} as const;

export const POSITIONS = ["QB", "RB", "WR", "TE"] as const;
export type Position = (typeof POSITIONS)[number];

export const MODEL_VERSION = "dg-value-1";
