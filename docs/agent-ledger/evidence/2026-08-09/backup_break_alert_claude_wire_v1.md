From Claude Code (implementing lane) — ⚠ URGENT: the 10:15 backup will FAIL in ~60 minutes

Full diagnosis: `docs/agent-ledger/evidence/2026-08-09/backup_break_alert_claude_v1.md`

Raised: 2026-08-09 09:11 EDT by Claude Code. **Read-only diagnosis; nothing changed.**

## The fact

`app/config/backup_manifest.json` in the **WORKING TREE** (uncommitted, `+5` lines, absent from
`HEAD`) declares a new required store:

```
{ "path": "app/data/sources/cfbd_fbs_schedules", "required": true, "kind": "directory" }
```

**That directory does not exist.** A read-only replay of the backup's own required-store validation
over all 39 required entries returns exactly one failure:

```
missing_required:app/data/sources/cfbd_fbs_schedules
```

`scripts/backup_irreplaceable_data.py:226-228` raises `BackupError` on that condition and the run
aborts before any upload. The script reads the manifest **from disk**, so the fact that the entry is
uncommitted gives no protection — the 10:15 LaunchAgent will read the working-tree file.

**Time to impact: ~64 minutes** (`com.davidleess.dynasty-backup-irreplaceable`, 10:15 local).

## What is NOT the cause

- **B21 is fine.** `app/data/sources/nflverse_schedules` is present with 6 files. Its manifest entry
  landed in the same commit as a populated store, exactly as the landing-order constraint required.
- The other 37 required entries all pass: present, real directories, non-empty.
- The last run succeeded — `20260808T141503Z`, `status: completed`, `sha256_verified: true`,
  `failures: []`.

## Why it happened, stated as a rule rather than a blame

This is the **landing-order hazard** flagged throughout the B21 cycle, now realised on the CFBD FBS
ticket: **a required manifest entry must never precede a populated store.** B21 honoured it. This
entry was added while its store is still being built.

The rule is mechanical and worth writing into the ticket template: *the manifest entry and the first
capture land together, or the manifest entry does not land.*

## Two ways to clear it, both quick

1. **Populate the store** — run the first CFBD FBS capture so the directory exists and holds at
   least one file. Paid CFBD is authorized (David, 2026-08-09: *"Paid CFBD is 100% authorized at all
   times"*), so nothing gates this except the route being ready. **Owner: the CFBD lane.**
2. **Remove the entry until the store exists** — revert those 5 uncommitted lines and re-add them
   with the capture. Safest, smallest, fully reversible.

**I have not done either.** The entry belongs to another lane's in-flight ticket, and removing it
unannounced would damage that work. This is a report, and the decision is David's or the owning
lane's.

## Verification anyone can rerun

```bash
.venv/bin/python3.14 -c "
import json, pathlib
m = json.loads(pathlib.Path('app/config/backup_manifest.json').read_text())
for e in m['required']:
    p = pathlib.Path(e['path'])
    if not p.exists(): print('MISSING', e['path'])
    elif e['kind'] == 'directory' and not any(x.is_file() for x in p.rglob('*')): print('EMPTY', e['path'])
"
```

PLEASE REPLY with: (a) you are populating app/data/sources/cfbd_fbs_schedules before 10:15, OR (b) you want the 5 uncommitted manifest lines reverted until the store exists — say which and I will act, OR (c) you have already handled it.
