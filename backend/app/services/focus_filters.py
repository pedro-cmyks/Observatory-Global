"""Focus-filter helpers shared by /api/v2/nodes and /api/v2/focus.

The universe/threads entry (spec 2026-07-02-universe-view.md; Pedro's
"llegar desde la nube") opens THREADS as the focus lens, but the theme
focus filter was GDELT-only (`$1 = ANY(themes)`) — thread ids
(dynamic-topic-<id> / atlas slugs) matched nothing, so every panel
silently stayed global. Thread-shaped theme values resolve through
typed membership instead.
"""


def thread_focus_filter(value: str) -> tuple[str, str] | None:
    """Return (filter_sql, param) when a theme-focus value is a THREAD id.

    GDELT codes are UPPER_SNAKE and never contain "-", so a hyphen reliably
    marks a thread id: `dynamic-topic-<id>`, `cluster-<id>`, or an atlas slug
    (optionally with the thread-list `--cc[-cc...]` suffix, which
    topic_members does not carry). Returns None for plain GDELT codes.
    """
    v = value.lower().strip()
    if "-" not in v:
        return None
    topic_id = v if v.startswith(("dynamic-topic-", "cluster-")) else v.split("--")[0]
    return (
        "id IN (SELECT signal_id FROM topic_members"
        " WHERE topic_id = $1 AND role = 'evidence' AND signal_id IS NOT NULL"
        " AND quarantined IS NOT TRUE)",
        topic_id,
    )
