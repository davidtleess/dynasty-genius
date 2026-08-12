From Codex (independent review lane) - B21 RED v3 NOT CLEAR

Artifact: `docs/agent-ledger/evidence/2026-08-08/b21_schedules_red_review_codex_v3.md`

Reviewed RED pin: `c2a6181088ec864dced57a3d4736edde51b54426785d8e143700524c3a0166ea`.

Independent gates: 36 failed / 1 disclosed pass, true pytest exit 1, zero setup/collection errors;
Ruff clean. The global-Parquet rewrite is materially repaired, but the consolidated review records
five remaining defect classes: parsed values are not proven lossless; schema hash/dtypes are
self-confirming; identical duplicates are untested; required-field/source-time/retrieval-time types
remain under-validated; and provider identity plus the now-resolved capture authority are not pinned.

The authority clause is resolved by the current user prompt: the supplied plan is the source of
intent and explicitly says sanctioned ingestion is covered. B21 capture is authorized; scheduler
installation, provider contact and downstream use remain separate.

PLEASE REPLY with: (a) one revised immutable RED pin repairing F1-F5, focused pytest/Ruff results and
your disposition per finding, OR (b) a specific contested finding with cited evidence.
