"""%-formatted SQL must have as many placeholders as arguments.

Caught live on 2026-08-12: hoisting a hardcoded interval into a constant was
written as

    \"\"\"... INTERVAL '\"\"\" + str(DAYS) + \"\"\" days' ... INTERVAL '%s hours'\"\"\" % (hours, hours)

`%` binds TIGHTER than `+`, so the format applied to the LAST fragment alone --
which carried one placeholder against two arguments. Every unit test passed
(they exercised pure functions) and the endpoint 500'd on the first real call.

This scans for the shape instead of the instance: any `<str literal> % <tuple>`
in a router must have matching arity, so the next hoist fails in CI rather than
in a reader's browser.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

ROUTERS = sorted((pathlib.Path(__file__).resolve().parents[1] / "app" / "routers").glob("*.py"))


def _format_sites(path: pathlib.Path):
    """Yield (lineno, placeholder_count, arg_count) for each `"..." % (...)`."""
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
        if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod)):
            continue
        try:
            template = ast.literal_eval(node.left)
        except Exception:
            continue
        if not isinstance(template, str) or "%s" not in template:
            continue
        if isinstance(node.right, ast.Tuple):
            arg_count = len(node.right.elts)
        else:
            # A single non-tuple operand formats exactly one placeholder.
            arg_count = 1
        yield node.lineno, template.count("%s"), arg_count


@pytest.mark.parametrize("path", ROUTERS, ids=lambda p: p.name)
def test_percent_formatted_sql_arity_matches(path: pathlib.Path):
    mismatches = [
        f"{path.name}:{lineno} has {placeholders} '%s' but {args} argument(s)"
        for lineno, placeholders, args in _format_sites(path)
        if placeholders != args
    ]
    assert not mismatches, "; ".join(mismatches)


def test_the_scanner_actually_finds_format_sites():
    """Guard the guard: a scanner that matches nothing would pass vacuously."""
    total = sum(len(list(_format_sites(p))) for p in ROUTERS)
    assert total > 0, "no %-formatted SQL found — the arity check is inert"
