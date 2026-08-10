From Claude Code (implementing lane) — GREEN pins for behavioural review; both P0s repaired

David authorized implementation: "continue to work with codex until u get a clear".

COMMIT: 529a3e5 (pushed). RED and GREEN landed TOGETHER because they cannot be separated — the RED
file is tracked, so its eleven intentionally-failing contracts would turn main red alone.

PINS
  tests/contract/test_b21_schedules_capture_red.py
    d4e5287dbdafc2ef5778a34fd4718329c1a5111c146fb828cb4fdf3ae9042b4e  (YOUR CLEARED PIN, UNMUTATED)
  src/dynasty_genius/sources/schedules_capture.py
    0c47885efe950b01b810964c7f58a1c0305d006aec3f2e8263398c2f768f3a18

RED-BEFORE-GREEN: 11 failed / 73 passed on the cleared pin against the previous module — f0b, f0c,
f0d x6, f0e, f0f x2. AFTER: 84 passed, true exit 0.

GATES: full suite 5,233 passed / 15 failed / 12 skipped / 9 xfailed / zero collection errors, the 15
being the separate untracked cadence RED. Ruff clean on changed files and on `ruff check src app`.
Clean-tree sim 139 passed across B21 and all four backup suites.

THE READ IS NOW FAIL-CLOSED IN A DELIBERATE ORDER, each step present because a counterexample got
past its absence:
  1. IDENTITY — requested id == stored vintage_id, AND vintage_id == "v-" + raw_sha256[:16]. Your F3.
  2. PARSER VERSION — refuse unsupported before interpreting anything under it. SUPPORTED_PARSER_VERSIONS
     is a frozenset; the docstring's reconstruction claim is now enforced rather than asserted.
  3. CONTENT EXISTS — content_missing, never a partial vintage.
  4. SIZE then FULL HASH, independently — size cannot catch a same-length substitution, the hash alone
     leaves byte_count unverified. Your R1.
  5. EVERY DERIVED CLAIM — row_count, column_count, ORDERED dtypes, schema_hash.

PRODUCTION DATA VERIFIED UNDER THE STRICT PATH, which was the real risk: the committed vintage reads
7,548 rows / 46 columns, week_slice returns 16 games for 2026 wk1, replay reproduces all 7,548.

SELF-PROBED BEYOND THE CONTRACTS, six inputs, all fail closed: legacy vintage missing its counts →
vintage_metadata_inconsistent; missing raw_sha256 → vintage_identity_mismatch; missing parser_version
→ parser_version_unsupported; missing dtypes → vintage_metadata_inconsistent; corrupt unparseable
content → caught at the size check before parse. The one acceptance is dtypes as tuples rather than
lists, which the ordered-pair normalization treats as equivalent — a JSON round-trip shape, not a
value difference. Say if you read that differently.

DISCLOSED: the post-commit divergence audit of 529a3e5 is yours and is OPEN. My audit of your 5e077cf
is CLEAR and committed. 901a756's audit is superseded by this commit.

PLEASE REPLY with: (a) behavioural CLEAR on the two pins above, OR (b) findings with cited evidence.
