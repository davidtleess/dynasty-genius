// The posture disclosure — `league_pulse_fe_mitigation_v1`.
//
// It says three things a posture word cannot say for itself: the labels are
// COMPUTED, they are computed from these four roster signals, and they are a
// read of the ROSTER rather than of the manager. The four weights below it
// mirror the registered POSTURE_SIGNAL_WEIGHTS export in
// src/dynasty_genius/team_posture.py (the graduation RED couples the two —
// change the producer weights without this mirror and tests fail).
//
// DG-114 extracted it from LeaguePulse.tsx unchanged, because the panel it
// covers moved. Partner Rankings prints `perspective_posture` and
// `counterparty_posture` and now lives on Trades; a posture word without this
// paragraph above it is a claim about a manager's intent that nobody can back.
// It renders wherever posture words render — that is the contract, not the
// address it used to have.
//
// DG-111 released the byte lock on the paragraph (David's 2026-08-29 ruling,
// recorded verbatim in the ticket). Every fact the lock protected survives, in
// the same DOM position ahead of every panel; only the register changed.
const POSTURE_BASIS = [
  { label: "starter-weighted model value", pct: "60%" },
  { label: "roster age profile", pct: "20%" },
  { label: "early draft-pick balance", pct: "15%" },
  { label: "taxi/development stash", pct: "5%" },
] as const;

export function PostureBasis() {
  return (
    <div
      className="dg-league-pulse__mitigation"
      data-mitigation-contract="league_pulse_fe_mitigation_v1"
    >
      <p className="dg-league-pulse__mitigation-copy">
        We label each team contending, rebuilding and so on by reading four things off
        its roster — starter-weighted model value, roster age profile, early draft-pick
        balance, and taxi/development stash — weighted as shown below. That is our read
        of the roster, not a read of the manager: what they actually intend to do, how
        they really value their own players, and whether they want to trade at all are
        things nobody can see from here.
      </p>
      <dl
        className="dg-league-pulse__mitigation-basis"
        data-testid="league-pulse-posture-basis"
      >
        {POSTURE_BASIS.map(({ label, pct }) => (
          <div key={label} className="dg-league-pulse__mitigation-basis-row">
            <dt>{label}</dt>
            <dd>{pct}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
