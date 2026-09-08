CREATE TABLE public.players (
  player_id TEXT PRIMARY KEY,
  full_name TEXT NOT NULL,
  first_name TEXT,
  last_name TEXT,
  position TEXT,
  team TEXT,
  age NUMERIC,
  birth_date DATE,
  years_exp INTEGER,
  college TEXT,
  draft_round INTEGER,
  draft_pick INTEGER,
  draft_year INTEGER,
  status TEXT,
  injury_status TEXT,
  headshot_url TEXT,
  fantasycalc_id TEXT,
  active BOOLEAN NOT NULL DEFAULT true,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX players_position_idx ON public.players (position);
CREATE INDEX players_name_idx ON public.players (lower(full_name));

CREATE TABLE public.player_days (
  id BIGSERIAL PRIMARY KEY,
  snapshot_date DATE NOT NULL,
  player_id TEXT NOT NULL REFERENCES public.players(player_id) ON DELETE CASCADE,
  our_value NUMERIC,
  our_rank INTEGER,
  our_pos_rank INTEGER,
  market_value NUMERIC,
  market_rank INTEGER,
  market_pos_rank INTEGER,
  margin NUMERIC,
  margin_pct NUMERIC,
  rank_margin INTEGER,
  tier TEXT,
  tier_basis JSONB,
  model_version TEXT,
  receipts JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (snapshot_date, player_id)
);
CREATE INDEX player_days_date_idx ON public.player_days (snapshot_date);
CREATE INDEX player_days_player_idx ON public.player_days (player_id, snapshot_date DESC);

CREATE TABLE public.league_teams (
  roster_id INTEGER PRIMARY KEY,
  owner_id TEXT,
  display_name TEXT,
  team_name TEXT,
  avatar TEXT,
  is_mine BOOLEAN NOT NULL DEFAULT false,
  wins INTEGER,
  losses INTEGER,
  ties INTEGER,
  points_for NUMERIC,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.roster_players (
  id BIGSERIAL PRIMARY KEY,
  roster_id INTEGER NOT NULL REFERENCES public.league_teams(roster_id) ON DELETE CASCADE,
  player_id TEXT NOT NULL,
  slot TEXT NOT NULL DEFAULT 'bench',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (roster_id, player_id)
);
CREATE INDEX roster_players_player_idx ON public.roster_players (player_id);

CREATE TABLE public.league_transactions (
  transaction_id TEXT PRIMARY KEY,
  type TEXT,
  status TEXT,
  week INTEGER,
  created_ms BIGINT,
  roster_ids INTEGER[],
  adds JSONB,
  drops JSONB,
  draft_picks JSONB,
  raw JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX league_transactions_created_idx ON public.league_transactions (created_ms DESC);

CREATE TABLE public.draft_picks (
  id BIGSERIAL PRIMARY KEY,
  season TEXT NOT NULL,
  round INTEGER NOT NULL,
  original_roster_id INTEGER NOT NULL,
  owner_roster_id INTEGER NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (season, round, original_roster_id)
);

CREATE TABLE public.sync_runs (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  rows_written INTEGER,
  detail JSONB
);
CREATE INDEX sync_runs_started_idx ON public.sync_runs (started_at DESC);

CREATE TABLE public.watchlist (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL,
  player_id TEXT NOT NULL REFERENCES public.players(player_id) ON DELETE CASCADE,
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, player_id)
);

GRANT SELECT ON public.players TO authenticated;
GRANT ALL ON public.players TO service_role;
GRANT SELECT ON public.player_days TO authenticated;
GRANT ALL ON public.player_days TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.player_days_id_seq TO service_role;
GRANT SELECT ON public.league_teams TO authenticated;
GRANT ALL ON public.league_teams TO service_role;
GRANT SELECT ON public.roster_players TO authenticated;
GRANT ALL ON public.roster_players TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.roster_players_id_seq TO service_role;
GRANT SELECT ON public.league_transactions TO authenticated;
GRANT ALL ON public.league_transactions TO service_role;
GRANT SELECT ON public.draft_picks TO authenticated;
GRANT ALL ON public.draft_picks TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.draft_picks_id_seq TO service_role;
GRANT SELECT ON public.sync_runs TO authenticated;
GRANT ALL ON public.sync_runs TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.sync_runs_id_seq TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.watchlist TO authenticated;
GRANT ALL ON public.watchlist TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.watchlist_id_seq TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.watchlist_id_seq TO service_role;

ALTER TABLE public.players ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.player_days ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.league_teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.roster_players ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.league_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.draft_picks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sync_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.watchlist ENABLE ROW LEVEL SECURITY;

CREATE POLICY "players readable by signed in users" ON public.players FOR SELECT TO authenticated USING (true);
CREATE POLICY "player_days readable by signed in users" ON public.player_days FOR SELECT TO authenticated USING (true);
CREATE POLICY "league_teams readable by signed in users" ON public.league_teams FOR SELECT TO authenticated USING (true);
CREATE POLICY "roster_players readable by signed in users" ON public.roster_players FOR SELECT TO authenticated USING (true);
CREATE POLICY "league_transactions readable by signed in users" ON public.league_transactions FOR SELECT TO authenticated USING (true);
CREATE POLICY "draft_picks readable by signed in users" ON public.draft_picks FOR SELECT TO authenticated USING (true);
CREATE POLICY "sync_runs readable by signed in users" ON public.sync_runs FOR SELECT TO authenticated USING (true);
CREATE POLICY "own watchlist" ON public.watchlist FOR ALL TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());