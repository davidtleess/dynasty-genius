// DG primitive: the metric cell — mono tabular value, right-aligned (numbers
// compare right-to-left digit by digit; benchmark craft mechanics), manager-
// language label, receipt one press away.
import { ReceiptTrigger } from "./ReceiptTrigger";
import "./ui.css";

export function MetricCell({
  label,
  value,
  receipt,
  emphasis,
}: {
  label: string;
  value: string;
  receipt?: { label: string; source: string; capturedAt: string } | undefined;
  /** Increment 0 (Codex R2): the one focal number per row. This variant —
   *  not ValueHero — carries row-level emphasis inside the 32px density. */
  emphasis?: "row-focal" | undefined;
}) {
  return (
    <span className="dg-ui-metric">
      <span className="dg-ui-metric__label">{label}</span>
      <span
        className={
          emphasis === "row-focal"
            ? "dg-ui-metric__value dg-ui-metric__value--emphasis"
            : "dg-ui-metric__value"
        }
        data-align="right"
        data-numeric="tabular"
        {...(emphasis !== undefined ? { "data-emphasis": emphasis } : {})}
      >
        {value}
      </span>
      {receipt && (
        <ReceiptTrigger
          label={label}
          capturedAt={receipt.capturedAt}
          source={`${receipt.label} · ${receipt.source}`}
        />
      )}
    </span>
  );
}
