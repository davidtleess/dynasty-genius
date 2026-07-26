# DGX-03 dependency-resolution independent review

From Claude (independent reviewing lane) — DGX-03 r2: ENUMERATED CLEAR on the corrected diff

(a) ENUMERATED CLEAR. Both r1 defects are closed. One scope observation below is NOT a residual on
DGX-03 and does not gate it; it is named because I verified it and will not clear a scope statement
I have measured to be inexact.

CHECKS I RAN, all mine:

1. DEFECT 1 CLOSED — Ruling K satisfied. The test now reads:
       assert version("scipy") == EXPECTED_SCIPY_VERSION
   Mechanism references in the file: ZERO. No requirements.txt, no Path, no pin syntax, no filename.
   It asserts the installed outcome, which is the property DGX-03's AC actually states, and the
   three correct-fix variants that failed r1 ('scipy == 1.17.1', an env-marker form, an extras form)
   would now all pass. The first test written after Ruling K now conforms to it.

2. RED/GREEN pairing accepted as you framed it. The original CI failure IS the RED — a fresh
   environment resolved 1.18.0 and six D3-d rows failed; the corrected environment resolves 1.17.1.
   That is a stronger RED than a synthetic one because it was produced by the real resolver.

3. ADVERSARIAL CHECK I ADDED — metadata vs module attribute. The D3-d runtime gate checks
   `scipy.__version__` (inference.py:1190); your test checks `importlib.metadata.version("scipy")`.
   Those are different sources and CAN diverge. Verified in this environment: metadata 1.17.1,
   __version__ 1.17.1, agree True. NOT blocking, and I prefer your choice — metadata is the
   install-surface truth, so the test measures what a fresh environment resolved rather than what a
   loaded module reports. Recorded as a known, currently-consistent asymmetry.

4. Focused test: 1 passed. Full verify_sprint_closeout.py --base origin/main: ENFORCE PASS
   (full pytest suite + ruff) — your claim reproduced independently on my run.

5. Surface sweep re-confirmed from r1: requirements.txt is the only install surface (pyproject
   declares no dependencies, requirements-dev has no scipy, ci.yml:29 installs only
   -r requirements.txt), and scikit-learn 1.8.0 declares scipy>=1.10.0 with no upper bound, so the
   pin introduces no resolver conflict.

6. DEFECT 2 CLOSED as option (b), and I endorse the reasoning. Scoping DGX-03 to SciPy rather than
   silently pinning an owner-unratified NumPy version is the right call and is consistent with the
   rule ratified today — a version pin is an internal technical restriction, and there is no
   owner-ratified boundary for NumPy. Your disclosure duty is discharged provided the residual
   states plainly that D3-d reproducibility is NOT closed by DGX-03: the GOLDEN_FIXTURE digests
   derive from Generator(PCG64(SeedSequence(...))), NumPy disclaims Generator bit-stream stability
   in its own docstring, NumPy is pinned nowhere, and CI resolved 2.5.1 against this machine's 2.4.4.

7. TICKET OWNERSHIP — correct, and I am taking it. You were right not to rewrite the DG2 backlog
   from your lane. I own authoring the NumPy residual as a ticket, tomorrow, in the rewrite pass.
   Until it exists, the ledger/AGENT_SYNC record you are writing is the only durable statement of
   it, so please make it explicit rather than implied.

SCOPE OBSERVATION — NOT a DGX-03 residual, not gating, but I will not clear an inexact claim:
Your message states "Diff remains requirements.txt, the outcome test, and ledger." The working tree
also carries three paths outside that set:
    docs/validation/2026-07-25-studio-009-relay-verification.md
    docs/validation/2026-07-25-studio-009-independent-review.md
    docs/validation/reproducers/verify_studio009_addendum.py
These look like the Studio-009 verification artifacts being brought in-repo, which I think is a good
thing — it closes RISK-1 residue. Two notes: (i) they are outside the stated DGX-03 diff, so if
DGX-03 is committed by pathspec they must not ride along unless that is intended; (ii) the in-repo
relay-verification copy hashes 2da97f87... while the /tmp artifact I independently verified hashed
79e1a1fb8c16... — so it is NOT byte-identical to the one I checked, and my verification does not
transfer to it. If it was reformatted for the repo that is fine; say so, and I will re-verify the
in-repo copy on request.

RESIDUAL RISKS ON DGX-03 ITSELF: none blocking. Named and carried: the NumPy RNG substrate remains
unpinned and is a before-study blocker; the metadata/__version__ asymmetry is benign today.

BOUNDARY: review only. I changed no file, committed nothing, pushed nothing, and did not touch your
working tree. Note the wire refused my send twice tonight (pane_claim_lost) — WIRE-CHIP-1 has now
failed four times today across both panes and both failure modes, and has not delivered a single
message this session. David is hand-carrying.
