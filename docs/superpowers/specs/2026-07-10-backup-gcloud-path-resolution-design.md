# Backup gcloud PATH Resolution — Design Spec

**Date:** 2026-07-10
**Status:** DRAFT — awaiting cockpit CLEAR, then David authorization to open the RED
**Authoring lane:** Claude (spec) · Codex (falsification + RED authorship) · Gemini (advisory)
**Scope:** `scripts/backup_irreplaceable_data.py` (the offsite-backup runner). No data, no model, no frontend.

---

## 1. Problem (measured, not inferred)

The daily offsite-backup LaunchAgent (`com.davidleess.dynasty-backup-irreplaceable.plist`, 10:15 local) **has never succeeded**. The live marker `app/data/ops/backup_status_latest.json`:

```json
{ "status": "failed", "failures": ["unexpected:FileNotFoundError"],
  "files": 0, "bytes": 0, "finished_at": "2026-07-10T14:15:00Z" }
```

It dies in **36 ms** with zero files staged. The earlier cause Codex flagged — `missing_required:market_divergence_history.db` — is **resolved**: that DB now exists (26 MB), and all 30 manifest-required files are present (verified).

### Root cause

`_real_gcloud_runner` (`scripts/backup_irreplaceable_data.py:306`) calls the bare binary name:

```python
subprocess.run(["gcloud", *args], ..., env={**os.environ, ...})
```

`gcloud` is installed at `/usr/local/bin/gcloud`. **launchd runs the job with the minimal default PATH** (`/usr/bin:/bin:/usr/sbin:/sbin`), which excludes `/usr/local/bin`. So the first gcloud call — `auth print-access-token` at `:183`, before any file is staged — raises `FileNotFoundError`, caught by the broad handler at `:272` and flattened to `unexpected:FileNotFoundError`.

### Reproduced (not asserted)

```
PATH=/usr/bin:/bin:/usr/sbin:/sbin  subprocess.run(["gcloud", ...])
  -> FileNotFoundError: [Errno 2] No such file or directory: 'gcloud'   # the marker's exact failure
PATH=/usr/local/bin:...             subprocess.run(["gcloud", "--version"])  -> rc 0
```

### Consequence

The irreplaceable forward-capture stores (`market_divergence_history.db`, `fc_forward_capture.db`, `model_forward_capture.db`, `fc_snapshots.db`) are **not protected offsite**. This is the real state behind the standing gate "backup must go green before any LaunchAgent install."

## 2. Design

Make the runner **PATH-independent** and make an absent binary a **named, actionable failure** instead of a mystery.

### 2.1 Resolve the binary to an absolute path

New pure helper (injectable seams so the RED needs neither gcloud nor a network nor a real FS):

```python
DEFAULT_GCLOUD_CANDIDATES = (
    "/usr/local/bin/gcloud",        # Intel Homebrew / Cloud SDK (this machine)
    "/opt/homebrew/bin/gcloud",     # Apple Silicon Homebrew
    "/usr/local/google-cloud-sdk/bin/gcloud",
)

def _resolve_gcloud_binary(
    *, which=shutil.which, is_file=os.path.isfile,
    candidates=DEFAULT_GCLOUD_CANDIDATES,
) -> str:
    found = which("gcloud")            # honor an explicit PATH if gcloud is on it
    if found:
        return found
    for candidate in candidates:       # fall back to well-known absolute locations
        if is_file(candidate):
            return candidate
    raise BackupError("gcloud_not_found")
```

### 2.2 Bind the resolved path — lazy factory inside `run_backup` (Codex-CLEARed shape)

**Decided (Codex review, 2026-07-10 CLEAR): resolve inside `run_backup`, not `main()`.** `run_backup` already owns the terminal marker state machine and staging cleanup, so resolving there keeps `gcloud_not_found` inside the named-failure path (`:270`) with no way to reintroduce a pre-marker crash, and it is hermetically testable without `main()` simulating a failed runner.

`run_backup` gains an injected seam `gcloud_runner_factory: Callable[[], Callable[[list[str]], Any]] | None = None`. It carries **no implicit real default** — like every other external-effect seam on `run_backup`, the caller binds it; `main()` binds `_real_gcloud_runner_factory` explicitly (making it implicit here would be more surprising, not less). It is called **once, inside the existing `try`**, before the first gcloud use; the factory resolves the binary via §2.1 and returns a bound runner:

```python
def _real_gcloud_runner_factory() -> Callable[[list[str]], Any]:
    gcloud_bin = _resolve_gcloud_binary()          # raises BackupError("gcloud_not_found") if absent
    def _runner(args: list[str]) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "CLOUDSDK_CORE_DISABLE_PROMPTS": "1"}
        return subprocess.run([gcloud_bin, *args], capture_output=True, text=True, env=env, check=False)
    return _runner
```

Inside `run_backup`'s `try`, before staging/auth:

```python
gcloud_runner = gcloud_runner_factory()            # BackupError here → clean :270 gcloud_not_found marker
```

The existing `gcloud_runner` parameter is retained for the test seam (tests inject a fake factory that returns a fake runner, or a factory that raises). `main()` binds `gcloud_runner_factory=_real_gcloud_runner_factory` and no longer needs to resolve or simulate anything.

Invariant: **no `unexpected:FileNotFoundError`; an absent binary is `gcloud_not_found`, written as a normal failed marker.**

### 2.3 Optional defense-in-depth (David decides, not required by this slice)

Add an `EnvironmentVariables`/`PATH` key (`/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin`) to the backup plist. With §2.1 the runner no longer depends on it, so this is belt-and-suspenders, not the fix. **Out of scope unless David wants it.**

## 3. Out of scope (named, not hidden)

- **Whether gcloud AUTH succeeds under launchd.** This fix removes the FileNotFound layer only. A real run may next surface a credentials/HOME issue — but after this fix it surfaces as a **named** gcloud failure (non-zero returncode → existing auth-failure handling at `:183`), not a mystery. The restore-drill verifier is the backstop; `sha256_verified` stays earned.
- Any change to the append-only upload contract, the restore drill, the manifest, or the marker schema.
- The market-divergence-refresh LaunchAgent install (separate, still David-gated).

## 4. Falsification seeds (the RED must contain these)

Codex authors the RED. Each must be red on `main` and pass only on the GREEN. All hermetic — injected `which` / `is_file` / fake `gcloud_runner`; **no real gcloud, no network, no gitignored artifact.**

| # | Seed | Required behavior |
|---|---|---|
| F1 | `which("gcloud")` returns `/usr/local/bin/gcloud` | resolver returns it; runner invokes that absolute path |
| F2 | `which` returns None, candidate `/usr/local/bin/gcloud` `is_file` | resolver returns the candidate |
| F3 | `which` returns None, Apple-Silicon candidate present | resolver returns `/opt/homebrew/bin/gcloud` |
| F4 | `which` None **and** no candidate exists | raises `BackupError("gcloud_not_found")` — **never** a bare `FileNotFoundError` |
| F5 | `run_backup` with an injected `gcloud_runner_factory` that resolves to nothing (or raises `gcloud_not_found`) | marker `status=failed`, `failures=["gcloud_not_found"]`, **not** `unexpected:FileNotFoundError`; no upload, no pointer advance; staging cleaned |
| F6 | `_real_gcloud_runner_factory` with injected `which`→abs path; the returned runner is called | the invoked argv[0] is the **absolute** path, not `"gcloud"` |
| F7 | regression | every existing `test_horizon0_backup_red.py` test still passes; `main()` binds `gcloud_runner_factory=_real_gcloud_runner_factory` and the injected-fake seam is preserved |

**Test-construction law:** the marker path (`app/data/ops/backup_status_latest.json`) is gitignored; tests must inject `staging_root`/paths into `tmp_path` and drive `run_backup` / the resolver directly — never assert the live marker.

## 5. Sequence

1. Cockpit CLEAR on this spec (Codex technical).
2. **David authorizes** the RED.
3. Codex authors the RED (F1–F7), demonstrably red on `main`.
4. Claude implements GREEN; full backup-test suite + ruff; self-probe the resolver matrix.
5. Codex independent review → CLEAR.
6. **Only then**, David-authorized: a real backup + restore-drill run to earn a green marker (`sha256_verified: true`). That real run is the true acceptance gate and may surface the §3 auth layer as the next named step.

## 6. Risks

| Risk | Mitigation |
|---|---|
| Hardcoded candidate paths rot on a machine move | `which` is tried first (honors a correct PATH); candidates are only the fallback; `gcloud_not_found` is actionable if all miss |
| The fix hides a deeper auth problem | Explicitly scoped out (§3); auth failure surfaces as a named non-zero gcloud return, and the restore drill gates the pointer |
| Changing `_real_gcloud_runner`'s signature breaks `main()` binding | F7 pins the existing suite; the closure keeps `run_backup`'s injected `gcloud_runner` contract unchanged |
