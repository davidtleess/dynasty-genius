# Footballguys Phase A RED v26 — Codex v1

> **Provenance correction, 2026-08-12:** Codex authored this RED. Claude session
> `c43d74ea-9a5a-4810-a7dc-c4df383ec255` independently authored the GREEN and reproduced the
> RED-side oracle defects; Claude session `7f9a8a50-d661-4a94-abd5-3313773bca9a` later mistook
> itself for the only Claude lane. The resulting retraction demand was withdrawn.

Date: 2026-08-12  
Layer: 1 — source intake and governed persistence  
Final frozen RED SHA-256: `9e0a861facd1e1502d66f9bc4672c2055ca7c1719483f387014b5d3453aa76e3`  
Size: 7,473 lines / 288,681 bytes  
Named baseline GREEN: `d551fb66cb741cd0e27a7deb86d42c22673601ca40327e8e4514d8dd27e90e17`

The earlier pin `656f3f1dd847dde56ceec6e730bb6f726126f71e63f7d260696bde97868caac3`
is WITHDRAWN. It contained three defective result oracles: an unseeded intake was required to
render `ready` rather than the honest `review_required`; a clock-ownership test opened Phase C;
and an explicit-read equality compared two different instants. Claude session `c43d74ea…`
independently reproduced all three defects while HOLDING the implementation. This final pin
corrects only those oracles.

## Binding delta

Six tests bind canonical value ownership:

1. intake with caller `isoformat()` allowed exactly once must complete successfully, call it
   once, retain one ZIP, commit one receipt, and render the honest unseeded
   `review_required` state;
2. the same control with two permitted calls must still call it only once and converge to the
   same terminal state;
3. semantic writing must never compare the caller-owned datetime after validation;
4. direct semantic reduction must never compare it;
5. read-model clock pinning must canonicalize before semantic reduction while keeping Phase C
   closed and exposing the retained latest-analysis-ready identity;
6. the explicit read instant must canonicalize before calendar evaluation, so a caller
   `astimezone()` override is never invoked and the output equals the ordinary base-datetime
   result for that exact instant.

## Measured baseline census

Exact strict command produced:

- 660 collected;
- 6 failed — exactly the new v26 controls;
- 654 passed — every inherited v25 contract;
- exit 1.

Focused v26 census: 6 failed / 0 passed. Ruff clean; strict compile and diff check clean.
The ownership repair shape passes 660/660 as a coherence control; that is not the implementing
lane's final gate.

## Adequacy

- The submitted v25 repair passes all 654 inherited contracts and fails all six new controls.
- Returning the original subclass after validation fails the two stateful intake controls.
- Canonicalizing only the writer clock still fails direct semantic/read-model and explicit-now
  controls.
- Catching downstream exceptions instead of canonicalizing cannot satisfy the successful intake
  convergence and equality positives.

## Freeze and scope

This RED is frozen until the implementing lane returns its complete GREEN gate. No commit, push,
capture, provider contact, scheduler, or Phase B/C/D action is authorized. QB rushing H2 remains
UNDER TEST with no result and is unrelated.
