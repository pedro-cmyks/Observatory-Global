# WIP Branch Triage

**Date:** 2026-07-13

**Canonical branch:** `v3-intel-layer`

The eight battery-preservation WIP branches were compared against current `v3`
by merge base, changed paths and file contents. No branch was deleted merely
because it was old.

## Deleted as fully absorbed

| Branch | Preserved work | Evidence of obsolescence |
|---|---|---|
| `claude/jovial-goldstine-c6c2b8` | useful-coverage junk gate | Seven of eight changed files are byte-identical to `v3`; the eighth has the same work plus the later heavy-job mutex. |
| `claude/elated-swartz-b3ab2a` | clustering recall fix | The delivery record is identical; current scripts contain the recall change plus the later junk gate and larger measured production default. |
| `claude/sweet-bose-c24dd7` | subject-geography/FIPS work | Current `v3` contains the same FIPS and geo-selection work plus the later Palestine ambiguity fix, HTML decoding and `KU`/`BX` normalization. |

Only the local branch refs were removed. No user data, commit objects or active
worktree directories were deleted.

## Retained because they contain unique work

| Branch | Unique delta | Next review |
|---|---|---|
| `claude/awesome-shamir-b2d741` | conflict-event to thread relationship receipts and panel expansion | Reconcile with #255 and the shipped typed Investigation Graph before cherry-picking. |
| `claude/nervous-cerf-d3695d` | precomputed Universe snapshot service/migration/cron | Benchmark against current universe latency and verify migration-number collision before integration. |
| `claude/priceless-cray-851372` | avoids per-frame App rerenders during grid drag/resize | Browser-test panel motion and persistence on current react-grid-layout. |
| `claude/great-jackson-b8cde3` | Narrative Threads and Signal Stream interaction refinements | Visual diff against current L2 before deciding whether still needed. |
| `claude/heuristic-sinoussi-cab790` | anomaly/source-integrity CSS readability pass | Batch into the next recorded L2 visual review. |

The older named Claude branches outside this eight-branch WIP set were not part
of this deletion pass. They require a separate ancestor/worktree audit because
some are still attached to preserved worktrees.
