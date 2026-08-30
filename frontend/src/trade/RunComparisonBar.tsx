// Prices the trade — one press, both lanes, two separate POSTs.
//
// The optional roster number is what the market lane needs to also price what
// the OTHER manager would have to cut. It shipped as a bare number box with the
// word "Counterparty" over it and nothing saying what it changes; both are
// fixed here (the voice guide banishes lab vocabulary from product surfaces).
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
      <div className="dg-run-bar__counterparty">
        <label className="dg-run-bar__label" htmlFor="dg-trade-other-roster">
          Their roster number <span className="dg-run-bar__optional">(optional)</span>
        </label>
        <input
          id="dg-trade-other-roster"
          className="dg-run-bar__input"
          type="number"
          inputMode="numeric"
          value={counterpartyRosterId ?? ""}
          onChange={(event) => {
            const raw = event.target.value.trim();
            onCounterpartyChange(raw === "" ? null : Number(raw));
          }}
        />
        <p className="dg-run-bar__help">
          Fill this in and we will also price what the other side would have to cut to
          fit the deal.
        </p>
      </div>
      <button type="button" className="dg-run-bar__run" onClick={onRun}>
        Price this trade
      </button>
    </div>
  );
}
