// DG primitive: the receipt — every number can disclose its provenance
// (vision §2). Focusable disclosure control: keyboard (Enter/Escape), touch,
// and click are first-class; hover is never the only path (seed-9 contract).
import { useState } from "react";
import "./ui.css";

export function ReceiptTrigger({
  label,
  capturedAt,
  source,
}: {
  label: string;
  capturedAt: string;
  source: string;
}) {
  const [open, setOpen] = useState(false);

  return (
    <span className="dg-ui-receipt">
      <button
        type="button"
        className="dg-ui-receipt__trigger"
        aria-label={`Provenance for ${label}`}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            setOpen(true);
          }
          if (event.key === "Escape") {
            setOpen(false);
          }
        }}
        onPointerDown={(event) => {
          if (event.pointerType === "touch") {
            setOpen(true);
          }
        }}
      >
        ⌗
      </button>
      {open && (
        <span className="dg-ui-receipt__panel" role="status">
          <span className="dg-ui-receipt__row" data-testid="receipt-raw-source">
            {source}
          </span>
          <span className="dg-ui-receipt__row" data-testid="receipt-raw-captured-at">
            {capturedAt}
          </span>
        </span>
      )}
    </span>
  );
}
