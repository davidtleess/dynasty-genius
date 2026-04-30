# Storage Strategy

This project should stay easy to understand, easy to back up, and safe to push to GitHub.

## Track in Git

Track files that define the system or preserve small, reviewable project state:

- Application code in `app/`
- Planning, architecture, and decision docs in `docs/`
- Project context files such as `AI_CONTEXT.md`, `CLAUDE.md`, and `README.md`
- Dependency manifests such as `requirements.txt`
- Small curated training snapshots that are needed to reproduce current model behavior
- Model run metadata and validation reports when they are small and useful for review
- Current tiny bootstrap model artifacts while the project is local and early-stage

## Do Not Track in Git

Do not commit generated or potentially large local data:

- Raw scrape dumps
- HTML/API response caches
- Browser automation artifacts
- Local scratch datasets
- Large processed datasets
- Repeated model artifacts once model runs become larger
- Secrets, API keys, cookies, session files, and local config

Current ignored locations:

- `app/cache/`
- `app/data/cache/`
- `app/data/raw/`
- `app/data/processed/`
- `app/data/artifacts/`
- `.pycache_tmp/`

## Current Transitional Policy

The current model pickles are tiny and useful for bootstrapping the app, so they can remain in git for now.

Revisit this once model artifacts or training data become large. At that point:

- Keep code, schemas, metadata, and validation reports in git.
- Move model binaries and large datasets to an artifact store.
- Keep only pointers/manifests in the repo.

Good future storage options:

- Local artifact directory excluded from git for early development
- GitHub Releases for occasional small versioned artifacts
- Cloudflare R2, S3, or similar object storage for durable model/data artifacts

## GitHub Rule

Before pushing to GitHub, check:

```bash
git status --short
git ls-files app/cache app/data/cache app/data/raw app/data/processed app/data/artifacts
```

The second command should return no generated cache/raw artifact files, except intentional `.gitkeep` placeholders.
