type SleeperTrade = {
  roster_action: string;
};

export function ReasonedSuppression({ trade }: { trade: SleeperTrade }) {
  return (
    <p>
      {/* banned-language-ok: mirrors the raw Sleeper transaction field for audit display */}
      {trade.roster_action}
    </p>
  );
}
