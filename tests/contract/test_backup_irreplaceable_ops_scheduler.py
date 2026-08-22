"""Contract: the offsite-backup launchd job must be able to reach gcloud.

2026-08-22. The 10:15 job failed on the migrated machine with
``failures: ["auth_unavailable"]`` and ``bytes: 0``. The cause is not credentials --
``gcloud auth print-access-token`` succeeds in an interactive shell. launchd runs the
job with ``PATH=/usr/bin:/bin:/usr/sbin:/sbin``, so the gcloud wrapper resolves
``python3`` to ``/usr/bin/python3`` (system 3.9) and refuses to load:

    ERROR: gcloud failed to load. You are running gcloud with Python 3.9, which is no
    longer supported by gcloud. Install a compatible version of Python 3.10-3.14 and
    set the CLOUDSDK_PYTHON environment variable to point to it.

Reproduced exactly with::

    env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME="$HOME" \
        /opt/homebrew/bin/gcloud auth print-access-token   # exit 1

and cleared by adding CLOUDSDK_PYTHON. Without this the daily offsite backup fails
every morning -- silently, because the failure only reaches a gitignored marker.

The plist is committable configuration only. Installing/reloading it with launchctl is
a separate David-gated machine change.
"""

from __future__ import annotations

import plistlib
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path("/Users/davidleess/dynasty-genius-product")
PLIST = Path("ops/launchd/com.davidleess.dynasty-backup-irreplaceable.plist")

MINIMUM_GCLOUD_PYTHON = (3, 10)


def _plist() -> dict:
    return plistlib.loads(PLIST.read_bytes())


def test_backup_launchd_plist_runs_the_backup_script_at_1015() -> None:
    data = _plist()
    args = data["ProgramArguments"]

    assert data["Label"] == "com.davidleess.dynasty-backup-irreplaceable"
    assert data["RunAtLoad"] is False
    assert data["WorkingDirectory"] == str(ROOT)
    assert data["StartCalendarInterval"] == {"Hour": 10, "Minute": 15}
    assert args[0] == str(ROOT / ".venv" / "bin" / "python3.14")
    assert args[1] == str(ROOT / "scripts" / "backup_irreplaceable_data.py")
    assert data["StandardOutPath"] == str(
        ROOT / "app/data/logs/backup_irreplaceable.out.log"
    )
    assert data["StandardErrorPath"] == str(
        ROOT / "app/data/logs/backup_irreplaceable.err.log"
    )


def test_backup_launchd_plist_declares_cloudsdk_python() -> None:
    """RED 2026-08-22: without this the job cannot authenticate under launchd."""
    data = _plist()

    assert "EnvironmentVariables" in data, (
        "the backup job needs CLOUDSDK_PYTHON; launchd's PATH resolves python3 to "
        "system 3.9 and gcloud refuses to load on it (auth_unavailable, bytes: 0)"
    )
    assert "CLOUDSDK_PYTHON" in data["EnvironmentVariables"]


def test_backup_cloudsdk_python_is_not_the_system_interpreter() -> None:
    """The whole point is to steer gcloud away from /usr/bin/python3 (3.9)."""
    interpreter = _plist().get("EnvironmentVariables", {}).get("CLOUDSDK_PYTHON")

    assert interpreter, "CLOUDSDK_PYTHON is unset"
    assert interpreter != "/usr/bin/python3"
    assert Path(interpreter).exists(), f"{interpreter} does not exist"


@pytest.mark.skipif(shutil.which("plutil") is None, reason="plutil is macOS-only")
def test_backup_launchd_plist_is_valid_plist() -> None:
    result = subprocess.run(
        ["plutil", "-lint", str(PLIST)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_backup_cloudsdk_python_satisfies_gclouds_floor() -> None:
    """gcloud requires 3.10-3.14. Assert the real binary, not the string."""
    interpreter = _plist().get("EnvironmentVariables", {}).get("CLOUDSDK_PYTHON")
    if not interpreter or not Path(interpreter).exists():
        pytest.fail("CLOUDSDK_PYTHON must point at an existing interpreter")

    result = subprocess.run(
        [interpreter, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    major, minor = (int(part) for part in result.stdout.strip().split("."))

    assert (major, minor) >= MINIMUM_GCLOUD_PYTHON, (
        f"gcloud refuses to load on {major}.{minor}; needs >= "
        f"{MINIMUM_GCLOUD_PYTHON[0]}.{MINIMUM_GCLOUD_PYTHON[1]}"
    )


# --------------------------------------------------------------------------
# 2026-08-22: the restore drill depends on a binary macOS can silently block.
#
# The backup uploads the ~1GB capture DBs as PARALLEL COMPOSITE objects. GCS
# stores no MD5 for a composite object -- only crc32c -- so the daily restore
# drill's hash comparison depends entirely on crc32c being computable. gcloud
# runs its interpreter with `-S`, so a `google-crc32c` wheel installed in any
# venv is invisible to it; it shells out to the bundled `gcloud-crc32c` binary
# instead.
#
# On a fresh SDK install that binary carries com.apple.quarantine. Gatekeeper
# blocks it, gcloud computes the destination hash as AAAAAA== (the hash of
# nothing), every large object "mismatches", and the run dies with
# upload_verification_mismatch AFTER a full 3.2GB upload. latest.json never
# advances, so the archive silently stops gaining new restore points.
#
# A gcloud upgrade re-downloads this binary and can re-quarantine it. This test
# is the tripwire.
# --------------------------------------------------------------------------

GCLOUD_CRC32C = Path("/opt/homebrew/share/google-cloud-sdk/bin/gcloud-crc32c")


@pytest.mark.skipif(not GCLOUD_CRC32C.exists(), reason="gcloud SDK not installed here")
def test_gcloud_crc32c_helper_is_executable_and_not_quarantined() -> None:
    """Gatekeeper-blocked helper => composite-object verification fails silently."""
    result = subprocess.run(
        [str(GCLOUD_CRC32C), "-o", "0", "-l", "16", "/etc/hosts"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, (
        f"{GCLOUD_CRC32C.name} would not run ({result.stderr.strip()}). If macOS "
        "blocked it, clear the quarantine:\n"
        f"    xattr -d com.apple.quarantine {GCLOUD_CRC32C}"
    )
    assert result.stdout.strip().isdigit(), (
        f"{GCLOUD_CRC32C.name} ran but returned no checksum: {result.stdout!r}. "
        "gcloud will compute AAAAAA== and every composite object will mismatch."
    )
