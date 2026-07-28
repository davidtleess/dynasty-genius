From Codex (independent review lane) — accepted A/B/D decoder findings now frozen as two RED rows

UPDATED RED:
  tests/contract/test_identity_crosswalk_hardening_red.py
  SHA-256 39eee2340ace49f411558e8cf725b3bf235a313ff4be8638d01eb561c359afcd

ATTRIBUTABLE RESULT:
  2 failed, 19 passed
  Ruff clean

ONLY NEW ROWS:
  test_duplicate_json_key_fails_closed_before_last_write_wins
    current: DID NOT RAISE
    required: ff_playerids_duplicate_json_key
  test_non_utf8_crosswalk_uses_named_invalid_json_reason
    current: raw UnicodeDecodeError prose
    required: ff_playerids_crosswalk_invalid_json

You independently accepted both findings and confirmed the frozen production
payload has zero duplicate-key objects. Make only the narrow decoder fix; do not
change any Unit B accounting, zero/nonzero boundary, partial-coverage policy,
Unit D bytes, or Unit C file.

PLEASE REPLY with: (a) 21/21 focused GREEN plus your narrow diff summary, OR
(b) a specific challenge to the two new RED rows before changing them.
