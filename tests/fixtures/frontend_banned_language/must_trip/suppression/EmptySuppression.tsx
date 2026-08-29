type SleeperTrade = {
  roster_action: string;
};

export function EmptySuppression({ trade }: { trade: SleeperTrade }) {
  return (
    <p>
      {/* banned-language-ok: */}
      {trade.roster_action}
    </p>
  );
}
