"""Adaptive per-centroid discussion threshold (Pedro's Pasta-Grannies case)."""
from app.services.public_attention import adaptive_noise_cut


def test_cut_rises_above_the_measured_background():
    # background hugging 0.87 ± 0.01 → cut ≈ 0.895, above the 0.82 floor
    sims = [0.87 + (i % 5 - 2) * 0.005 for i in range(100)]
    cut = adaptive_noise_cut(sims, floor=0.82)
    assert cut > 0.88
    # unrelated post at background level stays OUT; clear signal stays IN
    assert 0.87 < cut < 0.95


def test_small_sample_keeps_floor():
    assert adaptive_noise_cut([0.9] * 10, floor=0.82) == 0.82


def test_cut_never_below_floor():
    sims = [0.5] * 100
    assert adaptive_noise_cut(sims, floor=0.82) == 0.82
