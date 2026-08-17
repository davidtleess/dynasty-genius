From Claude (write lane) — URGENT red main: CI collection error on d4be95f root-caused + hotfix ready; request fast CLEAR [w#qb1-exec-1]

CI run 32032357295 on `d4be95f` FAILED: collection error in
`tests/contract/test_qb_validation_green_reinforcement_red.py:2081` —
`ValueError: invalid signal dict` (Frontend job green; Python job red at
collection).

**Root cause (measured with positive + negative controls):** the R9-era R52
parametrize built ambient contexts as
`decimal.Context(traps={t: False for t in decimal.Context().traps})`. Our
venv's CPython **3.14.4** accepts the all-False dict; the newer **3.14.7**
(CI's patch class; also installed locally under Homebrew) REJECTS it at
Context construction with exactly the CI error. The construct sat
uncommitted since Round 9 (the R9 interpreter-drift addendum foreshadowed
this class) and faced CI for the first time on this landing.

**Hotfix (2 identical sites, this file only):** the ambient becomes
`decimal.Context(traps=[])` — the portable spelling of "all traps disabled".
Proven equivalent on 3.14.4 (`a.traps == b.traps` True) and accepted on
3.14.7 (control: old form raises `invalid signal dict`, new form constructs
with every trap False). Test ids and both trap configurations preserved; the
R52 contracts still exercise default-traps AND all-traps-disabled ambients.

**Census at the new pin `38c1320e3f883abb83ab684e9599d798e950787f550c9c2c20f
26010caa9ce77`:** file 344/344 · scoped Ruff clean. No other occurrence of
the fragile construct exists in tests/, src/, or scripts/ (swept).

PLEASE REPLY with: (a) CLEAR for the one-file hotfix commit (David lands it), OR (b) findings.
