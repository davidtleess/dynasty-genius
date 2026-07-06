// DG primitive: the metric cell — mono tabular value, right-aligned (numbers
// compare right-to-left digit by digit; benchmark craft mechanics), manager-
// language label, receipt one press away.
import { ReceiptTrigger } from "./ReceiptTrigger";
import "./ui.css";

export function MetricCell({
  label,
  value,
  receipt,
}: {
  label: string;
  value: string;
  receipt?: { label: string; source: string; capturedAt: string } | undefined;
}) {
  return (
    <span className="dg-ui-metric">
      <span className="dg-ui-metric__label">{label}</span>
      <span className="dg-ui-metric__value" data-align="right" data-numeric="tabular">
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
