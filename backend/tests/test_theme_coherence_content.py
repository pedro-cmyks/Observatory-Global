"""#224 content-signal extension of the thread-coherence guard (2026-07-10).

Fixes the measured false negative: dt-755 "NATO Summit in Ankara" — an Arabic
front-page grab-bag — scored 0.617 "tight" in whitened cosine because
same-language content clusters with itself. The guard now also checks story
vocabulary / shared actors. These tests freeze the pure content-signal function
against synthetic versions of the measured pathologies.
"""
import app.main_v2  # noqa: F401 — resolve the app↔router import cycle first
from app.routers.themes import (
    COH_ACTOR_SHARE_MIN,
    COH_REPEATED_HEADLINE_MAX,
    COH_TOKEN_COVERAGE_MIN,
    _coherence_content_signals,
)


def _row(headline, source="wire.example", persons=None):
    return {"headline": headline, "source_name": source, "persons": persons or []}


class TestStoryTokenCoverage:
    def test_single_event_thread_has_high_coverage(self):
        # dt-1419 Keiko class: one story, shared vocabulary
        rows = [
            _row(f"Keiko Fujimori proclamada presidenta del Perú — nota {i}")
            for i in range(10)
        ]
        sig = _coherence_content_signals(rows)
        assert sig["storyTokenCoverage"] >= COH_TOKEN_COVERAGE_MIN

    def test_language_grab_bag_has_low_coverage_and_no_shared_actor(self):
        # dt-755 class: same language, unrelated stories, no shared vocabulary
        rows = [
            _row("هزة أرضية تضرب ولاية وهران الجزائرية"),
            _row("رياض محرز يعلن اعتزاله اللعب الدولي"),
            _row("انفجار غاز يحول حيا تركيا لساحة حرب"),
            _row("سعر صرف الدولار مقابل الليرة السورية"),
            _row("حريق مخزن بحاسي مسعود وفاة ثلاثة أشخاص"),
            _row("أردوغان وشهباز شريف يترأسان مباحثات"),
            _row("البيت الأبيض ترامب يلتقي الشرع وزيلينسكي"),
            _row("مظاهرة مناهضة لحلف الأطلسي في اسطنبول"),
            _row("عرض فيلمين جزائريين بميناء سيدي فرج"),
            _row("رئيس البرلمان العربي يشيد بالانجازات"),
        ]
        sig = _coherence_content_signals(rows)
        assert sig["storyTokenCoverage"] < COH_TOKEN_COVERAGE_MIN
        assert sig["topActorShare"] < COH_ACTOR_SHARE_MIN

    def test_outlet_suffix_tokens_do_not_count_as_story_vocabulary(self):
        # dt-755's top raw tokens were the En-Nahar outlet suffix repeated in
        # every headline. With the suffix stripped, otherwise-unrelated
        # headlines must read as LOW coverage, not suffix-inflated high.
        stories = [
            "زلزال يضرب وهران صباحا",
            "اعتزال اللاعب الدولي المخضرم",
            "ارتفاع اسعار الذهب عالميا",
            "انتخابات محلية الاسبوع المقبل",
            "حريق غابات قرب العاصمة",
            "افتتاح مستشفى جديد بالجنوب",
            "تراجع صادرات القمح هذا العام",
            "توقيف شبكة تهريب وقود",
            "مهرجان سينمائي ينطلق غدا",
            "امطار غزيرة تغلق الطرقات",
        ]
        rows = [
            _row(f"{s} – النهار أونلاين", source="النهار أونلاين ennaharonline")
            for s in stories
        ]
        sig = _coherence_content_signals(rows)
        assert sig["storyTokenCoverage"] < COH_TOKEN_COVERAGE_MIN

    def test_multilingual_single_event_keeps_shared_actor(self):
        # Cross-language real story: token coverage may split across scripts,
        # but latin-normalized persons stay shared → actor conjunction protects
        rows = [
            _row("Putin warns NATO over Poland", persons=["vladimir putin"]),
            _row("بوتين يحذر الناتو بشأن بولندا", persons=["vladimir putin"]),
            _row("Путін погрожує НАТО через Польщу", persons=["vladimir putin"]),
            _row("Putin advierte a la OTAN sobre Polonia", persons=["vladimir putin"]),
            _row("Poutine met en garde l'OTAN", persons=["vladimir putin"]),
            _row("Putin warnt die NATO vor Polen", persons=["vladimir putin"]),
        ]
        sig = _coherence_content_signals(rows)
        assert sig["topActorShare"] >= COH_ACTOR_SHARE_MIN


class TestRepeatedHeadlineShare:
    def test_front_page_dump_detected(self):
        # the "جريدة البلاد" pattern: identical headline from many outlets
        rows = [_row("جريدة البلاد", source=f"outlet{i}.example") for i in range(8)]
        rows += [_row("قصة حقيقية عن قمة أنقرة")] * 2
        sig = _coherence_content_signals(rows)
        assert sig["repeatedHeadlineShare"] >= COH_REPEATED_HEADLINE_MAX

    def test_html_entities_normalized_before_comparison(self):
        rows = [_row("&#x62C;&#x631;&#x64A;&#x62F;&#x629; example")] * 5 + [
            _row("جريدة example")
        ]
        sig = _coherence_content_signals(rows)
        # unescaped form of the entity string equals the literal string
        assert sig["repeatedHeadlineShare"] == 1.0

    def test_diverse_headlines_low_repeat(self):
        rows = [_row(f"Historia distinta numero {i} con palabras {i}") for i in range(10)]
        sig = _coherence_content_signals(rows)
        assert sig["repeatedHeadlineShare"] <= 0.1
