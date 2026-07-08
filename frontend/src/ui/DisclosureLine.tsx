// DG primitive: the standard non-decision-grade disclosure (H1 locked string;
// the API field decision_supported=false speaks here in manager language).
import { DISCLOSURE_LINE } from "../lib/copy";
import "./ui.css";

export function DisclosureLine() {
  return <p className="dg-ui-disclosure">{DISCLOSURE_LINE}</p>;
}
