"""Root's last same-bytes finding: the audit read the league snapshot a second time to hash it
for the report while the binding and the parse used the first capture. The script must capture
the snapshot bytes exactly once and derive every hash from that buffer."""
from __future__ import annotations

import re
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "dg178" / "audit_roster_coverage.py"


def test_the_audit_captures_the_snapshot_bytes_once_and_never_rehashes_a_fresh_read() -> None:
    src = SCRIPT.read_text()
    assert len(re.findall(r"a\.snapshot\.read_bytes\(\)", src)) == 1, "the snapshot must be read exactly once"
    assert "sha(a.snapshot)" not in src, "the report must reuse the captured snapshot_sha256, not re-hash a fresh read"
    assert "a.snapshot.read_text(" not in src and "json.load(a.snapshot" not in src
    assert src.count("snapshot_sha256") >= 3  # captured once, used for the binding and the report
