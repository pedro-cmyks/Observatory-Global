"""Pure-helper tests for the dossier connection endpoint (dossier-connections-v0)."""
from app.routers import dossier


def test_base_topic_id_strips_country_scope():
    assert dossier._base_topic_id("armed-conflict-escalation--CO") == "armed-conflict-escalation"
    assert dossier._base_topic_id("dynamic-topic-84") == "dynamic-topic-84"
    assert dossier._base_topic_id("  spaced--US ") == "spaced"


def test_cosine_bounds():
    assert dossier._cosine([1, 0, 0], [1, 0, 0]) == 1.0
    assert dossier._cosine([1, 0, 0], [0, 1, 0]) == 0.0
    assert dossier._cosine([0, 0, 0], [1, 1, 1]) == 0.0  # zero vector guarded


def test_project_positions_needs_three_and_is_normalized():
    assert dossier._project_positions({"a": [1, 0], "b": [0, 1]}) == {}  # < 3 → none
    pos = dossier._project_positions({
        "a": [1, 0, 0, 0], "b": [0, 1, 0, 0], "c": [0, 0, 1, 0], "d": [0.5, 0.5, 0, 0],
    })
    assert set(pos) == {"a", "b", "c", "d"}
    for p in pos.values():
        assert 0.0 <= p["x"] <= 1.0 and 0.0 <= p["y"] <= 1.0


def test_distinctive_df_max_allows_shared_actor_at_two_pins():
    # N=2: any actor shared by both pins has df=2 — must count (the NATO-Ankara
    # erdogan case). df<=1 here made shared_person edges impossible.
    assert dossier._distinctive_df_max(2) == 2
    assert dossier._distinctive_df_max(1) == 2
    assert dossier._distinctive_df_max(0) == 2


def test_distinctive_df_max_rarity_gate_at_larger_pin_sets():
    # The #234 guard stays for many pins: minority-share only, capped at 3.
    assert dossier._distinctive_df_max(3) == 2   # ceil(1.2)
    assert dossier._distinctive_df_max(5) == 2   # ceil(2.0)
    assert dossier._distinctive_df_max(8) == 3   # ceil(3.2) capped
    assert dossier._distinctive_df_max(16) == 3  # cap holds


# ── Frank v2 blocker 2: junk-actor filter ─────────────────────────────────────

def test_clean_actor_keeps_real_people_drops_ner_junk():
    assert dossier._is_clean_actor("tayyip erdogan") is True
    assert dossier._is_clean_actor("recep tayyip erdogan") is True
    # tokenizer artifact — repeated token
    assert dossier._is_clean_actor("states states") is False
    # the Black Sea in Romanian — multilingual geo-feature token
    assert dossier._is_clean_actor("marea neagra") is False
    assert dossier._is_clean_actor("mar negro") is False
    # gazetteer place/org names are never actors
    assert dossier._is_clean_actor("united nations") is False
    assert dossier._is_clean_actor("corea del sur") is False


# ── Frank v2 blocker 1: text-level cross-reference ────────────────────────────

def _hl(*headlines):
    import re
    return [(h.lower(), frozenset(re.split(r"[^\w]+", h.lower()))) for h in headlines]


def test_label_key_tokens_drops_stopwords_and_short_tokens():
    assert dossier._label_key_tokens("NATO Summit Ankara") == ["nato", "summit", "ankara"]
    assert dossier._label_key_tokens("The News of the Day") == ["day"]
    assert dossier._label_key_tokens("") == []


def test_mention_terms_finds_the_nato_summit_case():
    # The killer: tariff pin's own headline mentions the NATO pin's label.
    headlines = _hl("Trump orders cutoff of U.S. trade with Spain during NATO summit")
    terms = dossier._mention_terms(headlines, ["nato", "summit", "ankara"], [])
    assert terms == ["nato summit"]


def test_mention_terms_requires_two_label_tokens():
    # ONE generic shared token must not fire ("summit" alone).
    headlines = _hl("Leaders gather for climate summit in Belem")
    assert dossier._mention_terms(headlines, ["nato", "summit", "ankara"], []) == []


def test_mention_terms_single_token_label_fires_on_one():
    headlines = _hl("Protests spread across Venezuela after quake")
    assert dossier._mention_terms(headlines, ["venezuela"], []) == ["venezuela"]


def test_mention_terms_matches_actor_names_verbatim():
    headlines = _hl("Erdogan hosts leaders as tensions rise")
    # actor substring is matched on the raw lowered headline
    terms = dossier._mention_terms(
        _hl("Tayyip Erdogan hosts leaders as tensions rise"),
        ["unrelated", "label"], ["tayyip erdogan"],
    )
    assert "tayyip erdogan" in terms
    assert dossier._mention_terms(headlines, ["unrelated", "label"], ["tayyip erdogan"]) == []


# ── Synthesis prompt: text mentions + lens note reach the model ───────────────

def test_synth_user_renders_text_mentions_and_lens_note():
    req = dossier.SynthesizeRequest(
        title="NATO-Ankara",
        pins=[dossier.SynthPin(label="Tariff pin", evidence=["Trump orders cutoff — Reuters, 2026-07-08"])],
        connection=dossier.SynthConnection(
            state="split",
            nodes=[dossier.SynthConnectionNode(
                label="Tariff pin", connectedness="text-linked",
                text_mentions=["evidence text mentions 'nato summit' (NATO Summit Ankara)"],
            )],
            lens_note="Coverage lens: evidence leans Romanian-language sources (44%).",
        ),
    )
    out = dossier._synth_user(req)
    assert "text-linked" in out
    assert "evidence text mentions 'nato summit'" in out
    assert "coverage lens: Coverage lens: evidence leans Romanian" in out
    assert "2026-07-08" in out


def test_synth_user_keeps_coverage_country_out_of_confirmed_spine():
    req = dossier.SynthesizeRequest(
        pins=[dossier.SynthPin(label="Iran talks", evidence=["Talks continue"])],
        connection=dossier.SynthConnection(
            state="context-only",
            nodes=[dossier.SynthConnectionNode(
                label="Iran talks",
                connectedness="coverage-context",
                contextual_with=["Power outage"],
            )],
        ),
    )
    out = dossier._synth_user(req)
    assert "coverage-context" in out
    assert "coverage-country context only" in out
    assert "Power outage" in out


def test_synth_system_carries_glassbox_and_text_mention_rules():
    s = dossier._SYNTH_SYSTEM
    assert "TEXT MENTIONS OVERRIDE" in s
    assert "GLASS BOX" in s
    assert "YYYY-MM-DD" in s


def test_truncation_variant_prefix_rule():
    # inline rule mirrored from the edge loop: keep only the longest form
    shared = ["tayyip erdo", "tayyip erdogan"]
    kept = [p for p in shared if not any(q != p and q.startswith(p) for q in shared)]
    assert kept == ["tayyip erdogan"]
