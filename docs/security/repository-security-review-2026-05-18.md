# Repository Security Review — 2026-05-18

Scope: targeted repository hygiene review focused on accidental secret exposure, ignored files, local runtime artifacts, and public documentation.

## Result

No committed production secrets were found in the targeted scan.

The scan looked for common token/key patterns, database URLs, private keys, service-role markers, and provider key names outside ignored dependency folders.

## Findings

### Fixed: Python virtual environment was tracked

`backend/.venv/` had thousands of dependency files tracked in git. This is not a direct secret leak by itself, but it increases repository size, makes security review noisy, and can accidentally preserve local machine artifacts.

Resolution:

- Removed `backend/.venv/` from the git index.
- Added `backend/.venv/` to `.gitignore`.

### Fixed: local checkpoint files were tracked

Backfill checkpoint files under `checkpoints/` were tracked. These are runtime state, not source.

Resolution:

- Removed checkpoint files from git.
- Added `checkpoints/` to `.gitignore`.

### Fixed: duplicate copy files were tracked

Several ` 2` duplicate files existed in migrations and deprecated frontend code. They were byte-identical copies or generated timestamp artifacts.

Resolution:

- Removed duplicate migration/checkpoint/legacy frontend artifacts.

## Notes

`.env` exists locally and is ignored. That is expected. Do not commit local environment files.

The repository intentionally keeps `.env.example` files with placeholder values only.

## Remaining Recommendations

- Keep provider keys only in Fly.io, Vercel, Supabase, and Upstash secret stores.
- Run a full repository-wide security scan before public release or before adding authentication.
- Consider adding automated secret scanning in CI if the repository becomes public-facing or has more contributors.
