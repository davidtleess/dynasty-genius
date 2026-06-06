// Runs the two-lane comparison. The counterparty-roster selector is optional
// (default off = single-sided market reconciliation); when set, the market
// lane prices the counterparty's forced cuts too.
export function RunComparisonBar({
  counterpartyRosterId,
  onCounterpartyChange,
  onRun,
}: {
  counterpartyRosterId: number | null;
  onCounterpartyChange: (value: number | null) => void;
  onRun: () => void;
}) {
  return (
    <div className="dg-run-bar">
      <label className="dg-run-bar__counterparty">
        Counterparty roster (optional)
        <input
          type="number"
          value={counterpartyRosterId ?? ""}
          onChange={(event) => {
            const raw = event.target.value.trim();
            onCounterpartyChange(raw === "" ? null : Number(raw));
          }}
        />
      </label>
      <button type="button" className="dg-run-bar__run" onClick={onRun}>
        Run comparison
      </button>
    </div>
  );
}
