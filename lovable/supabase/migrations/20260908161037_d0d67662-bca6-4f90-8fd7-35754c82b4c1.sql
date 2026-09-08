GRANT SELECT ON public.players TO anon;
GRANT SELECT ON public.player_days TO anon;
GRANT SELECT ON public.league_teams TO anon;
GRANT SELECT ON public.roster_players TO anon;
GRANT SELECT ON public.league_transactions TO anon;
GRANT SELECT ON public.draft_picks TO anon;
GRANT SELECT ON public.sync_runs TO anon;

CREATE POLICY "players readable by anyone" ON public.players FOR SELECT TO anon USING (true);
CREATE POLICY "player_days readable by anyone" ON public.player_days FOR SELECT TO anon USING (true);
CREATE POLICY "league_teams readable by anyone" ON public.league_teams FOR SELECT TO anon USING (true);
CREATE POLICY "roster_players readable by anyone" ON public.roster_players FOR SELECT TO anon USING (true);
CREATE POLICY "league_transactions readable by anyone" ON public.league_transactions FOR SELECT TO anon USING (true);
CREATE POLICY "draft_picks readable by anyone" ON public.draft_picks FOR SELECT TO anon USING (true);
CREATE POLICY "sync_runs readable by anyone" ON public.sync_runs FOR SELECT TO anon USING (true);