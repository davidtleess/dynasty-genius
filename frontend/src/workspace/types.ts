import type { ReactNode } from "react";
import type { MarketRankPlayer, MarketRanksAvailable } from "../lib/api";
import type {
  ComparisonPayload,
  ComparisonPlayer,
} from "../research/comparisonHelpers";

export type WorkspaceView =
  | "today"
  | "roster"
  | "available"
  | "watchlist"
  | "compare"
  | "history";
export type WorkspaceOrder = "ours" | "market" | "gap" | "now" | "future" | "name";
export type WorkspacePlayer = {
  id: string;
  name: string;
  position: string;
  team: string | null;
  ownership: "roster" | "available" | "league" | "outside" | "unknown";
  rank: MarketRankPlayer | null;
  forecast: ComparisonPlayer | null;
  watched: boolean;
  watchedAt: string | null;
};
export type WorkspaceFrameProps = {
  view: WorkspaceView;
  onNavigate: (view: WorkspaceView) => void;
  query: string;
  onQuery: (query: string) => void;
  counts: { roster: number | null; available: number | null; watchlist: number };
  source: {
    forecastDate: string;
    marketDate: string;
    ownershipDate: string;
    commonPlayers: number;
  } | null;
  children: ReactNode;
};
export type WorkspaceBoardProps = {
  rows: WorkspacePlayer[];
  order?: WorkspaceOrder;
  data: MarketRanksAvailable;
  nowLabel: string;
  futureLabel: string;
  onWatch: (player: WorkspacePlayer) => void;
  onCompare: (player: WorkspacePlayer) => void;
};
export type WorkspacePlayerPanelProps = Omit<WorkspaceBoardProps, "rows"> & {
  player: WorkspacePlayer;
};
export type WorkspaceCompareProps = {
  players: WorkspacePlayer[];
  data: MarketRanksAvailable;
  comparison: ComparisonPayload;
  selection: { availableId: string | null; rosterId: string | null };
  onSelect: (selection: {
    availableId: string | null;
    rosterId: string | null;
  }) => void;
};
