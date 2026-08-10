# Footballguys Phase A RED — pre-capture manifest amendment

Date: 2026-08-10  
Author: Codex, RED owner  
Disposition: **Claude counter-finding accepted.**  
Superseded RED pin:
`1130f2bcde14ef8cc4d4bbba7e8eff8fbf71734a5388116053388b7d8d1bea7f`  
Amended RED path: `tests/contract/test_footballguys_phase_a_red.py`  
Amended SHA-256: `35e48037034983234fd05f66cc22876ece713bfe99e7db89b841e417bba600aa`  
Measured size: 1,329 lines / 55,974 bytes

## Counter-finding reproduced

`scripts/backup_irreplaceable_data.py` rejects any `required: true`, `kind: "directory"` store
that expands to zero files with `directory_empty_required:<path>`. This is an intentional DGX-02
anti-silence guard. The production `app/data/footballguys/objects/` directory currently contains
zero member files and must remain empty until David separately authorizes the first real paid drop.

Therefore a required objects-directory row in the pre-capture GREEN would make the nightly backup
fail before any provider archive exists to protect. Keeping the row required would force provider
bytes into the RED+GREEN landing, contradicting this cycle's explicit no-provider-data scope.

## Amendment

The RED now expects:

```text
app/data/footballguys/objects -> kind=directory, required=false
```

This is **pre-capture epoch only**. Optional means the existing backup runner covers the directory
whenever files exist but tolerates the intentionally empty pre-capture store. It does not make an
irreplaceable archive forever optional.

The first-real-capture change set has a closed landing-order obligation:

1. amend the RED expectation from `required=false` to `required=true`;
2. flip the production manifest row to `required=true` in the same reviewed act;
3. only then write the first provider archive, so the directory is non-empty when DGX-02 scans it.

The receipt and semantics databases remain required option-1 stores. `observations.db` remains an
optional transition/counterpart store because option 3 is inactive.

## Census

The number of contracts is unchanged: **185**. Against the implementing lane's current GREEN,
whose manifest still carries the superseded required row, the amended RED produces exactly:

```text
1 failed, 184 passed in 8.93s
```

The sole failure is:

```text
test_p0_option1_manifest_covers_every_durable_store[objects]
```

That is the intended handoff signal. Flipping only the pre-capture manifest row to optional should
restore **185/185** without changing production intake behavior.

Supporting checks: `py_compile` exit 0; Ruff clean; `git diff --check` clean. Codex changed only
the RED plus evidence/ledger. No production, manifest, ignore, runtime, provider, scheduler,
Phase B/C/D, commit, or push action was taken.
