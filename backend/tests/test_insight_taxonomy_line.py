"""The Analysis and the chart under it must describe ONE taxonomy.

Re-judge 2026-08-13 §4a, third charge: the paragraph named GDELT theme codes
while the category chart four inches below it read "Armed conflict escalation
4,754 / Crime & Justice 2,670" — "with no reconciliation". Two taxonomies, one
screen, nothing saying they were different populations.

The page already committed to Atlas R3 categories as the user-facing lens
(#249: the chart prints `category_counts` and falls back to "By Theme" only
when no category is live). The prompt now reads the SAME lane in the SAME
order, and names it, so the two blocks cannot disagree — and when the category
lane is empty both blocks fall back to themes together.
"""

from app.services.insight_text import taxonomy_line

CATEGORIES = [
    {"category": "Armed conflict escalation", "signals": 4754},
    {"category": "Crime & Justice", "signals": 2670},
    {"category": "crime-and-accidents", "signals": 900},
]
THEMES = [
    {"theme": "WB_696_PUBLIC_SECTOR_MANAGEMENT"},
    {"theme": "CRISISLEXREC"},
    {"theme": "UNGP_FORESTS_RIVERS_OCEANS"},
    {"theme": "HISTORIC"},
]


def test_categories_win_and_the_line_names_its_taxonomy():
    line = taxonomy_line(CATEGORIES, THEMES)
    assert "Atlas categories" in line
    assert "Armed conflict escalation" in line
    assert "Crime & Justice" in line
    # the GDELT lane must not leak in beside them
    assert "Public Sector" not in line


def test_a_slug_category_is_humanized_in_the_line():
    line = taxonomy_line(CATEGORIES, THEMES)
    assert "Crime and Accidents" in line
    assert "crime-and-accidents" not in line


def test_the_line_points_at_the_block_the_reader_can_see():
    """So the prose can say where the numbers under it come from."""
    assert "charted below" in taxonomy_line(CATEGORIES, THEMES)


def test_themes_are_the_fallback_only_and_are_named_as_such():
    line = taxonomy_line([], THEMES)
    assert "GDELT themes" in line
    assert "Public Sector Management" in line


def test_the_fallback_drops_every_code_it_cannot_name():
    """The exact witness codes, gone rather than title-cased."""
    line = taxonomy_line([], THEMES)
    assert "Crisislexrec" not in line
    assert "CRISISLEXREC" not in line
    assert "Ungp" not in line
    assert "Historic" not in line
    assert "Forests, Rivers and Oceans" in line  # this one HAS a human name


def test_no_nameable_row_anywhere_means_no_line_at_all():
    """Honest absence: the paragraph simply does not discuss themes."""
    assert taxonomy_line([], [{"theme": "CRISISLEXREC"}, {"theme": "HISTORIC"}]) is None
    assert taxonomy_line([], []) is None
    assert taxonomy_line(None, None) is None


def test_the_line_is_capped_and_keeps_the_served_order():
    rows = [{"category": f"Category {i}"} for i in range(9)]
    line = taxonomy_line(rows, [])
    assert "Category 0" in line and "Category 4" in line
    assert "Category 5" not in line
    assert line.index("Category 0") < line.index("Category 1")


def test_the_line_is_one_prompt_bullet():
    line = taxonomy_line(CATEGORIES, THEMES)
    assert line.startswith("- ")
    assert "\n" not in line
