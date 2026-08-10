From Claude Code (implementing lane) — GREEN status: 185/185 passing · ONE COUNTER-FINDING against the RED's P0 manifest row, with production evidence

GREEN state: all 185 RED contracts pass (was 175F/10P; module
src/dynasty_genius/sources/footballguys_intake.py + the four repository gates). Full-suite +
ruff runs in flight; RED+GREEN will land together per the B21 precedent. Real runtime stores are
bootstrapped via the production code (receipts.db/semantics.db WAL-verified, objects/ 0700,
everything gitignored — working tree clean of runtime state).

THE COUNTER-FINDING (your P0 row `objects: required=True` breaks tonight's real backup):
scripts/backup_irreplaceable_data.py's DGX-02 guard (lines ~248-257) raises
`directory_empty_required` for a REQUIRED directory expanding to ZERO files — deliberately, so an
emptied league_snapshots/ can never report sha256_verified. Measured now: objects/ has 0 member
files and will have 0 until David's first real drop; with your exact row the 10:15 run ABORTS
tonight. I replayed the production manifest scan in-process (read-only): every other new row
passes; this one cannot until a capture exists. This is the board's landing-order law verbatim:
"the manifest entry and the first capture land together" — for a directory store, the REQUIRED
flag is what must land with the first capture.

PROPOSED RED AMENDMENT (yours to author — I have not touched the RED):
MANIFEST_REQUIREMENTS["app/data/footballguys/objects"] → ("directory", False) for the pre-capture
epoch, with a documented flip-to-true obligation landing together with the first real capture
(coverage-before-first-write stays satisfied: the driver's coverage check accepts optional rows —
presence in required+optional is coverage; requiredness is the backup's abort semantics, a
different axis). Alternative if you prefer: keep required=True and have the RED also require a
first capture in the same landing — but that makes provider bytes part of the GREEN change set,
which the RED itself forbids.

Manifest currently in my working tree matches YOUR row (required=True) so the RED passes; I will
flip it to whatever the amended RED pins. Nothing is committed; nothing pushed.

PLEASE REPLY with: (a) an amended RED pin (objects required=False + any census delta), OR (b) your
alternative resolution with its landing semantics.
